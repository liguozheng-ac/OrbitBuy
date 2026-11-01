"""对本地 OrbitBuy 补充接手验收，独立测试买家；--with-model 会产生模型调用费用。

不修改服务器配置，不批准订单；收藏删除、个人 Skill 软删除、自动化归档。
会保留测试会话、Skill 历史和执行审计。输出仅针对合成测试数据。
运行：python -m scripts.verify_takeover --with-model
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
import uuid

import httpx


class Audit:
    def __init__(self, base, output, with_model):
        if urlsplit(base).hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("验收脚本仅允许连接本机")
        self.output = output
        output.mkdir(parents=True, exist_ok=False)
        self.client = httpx.Client(base_url=base, trust_env=False, timeout=180)
        self.with_model = with_model
        self.buyer = "takeover-" + uuid.uuid4().hex[:12]
        self.session = self.buyer + "-form"
        self.results, self.http = [], []
        self.skill = self.task = None

    def save(self, name, value):
        raw = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        raw = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "[REDACTED]", raw)
        (self.output / name).write_text(raw, encoding="utf-8")

    def check(self, name, condition, detail=None, status="pass"):
        row = {"name": name, "status": status if condition else "fail", "detail": detail}
        self.results.append(row)
        self.save("checks.json", self.results)
        print(f"{row['status']}: {name}", flush=True)

    def req(self, method, path, *, expected=200, buyer=True, **kwargs):
        params = dict(kwargs.pop("params", {}))
        if buyer:
            params.setdefault("buyer_id", self.buyer)
        response = self.client.request(method, path, params=params, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = {"text": response.text[:2000]}
        self.http.append({"method": method, "path": path, "params": params,
                          "request": kwargs.get("json"), "status": response.status_code,
                          "response": body})
        self.save("http.json", self.http)
        if response.status_code != expected:
            raise AssertionError(f"{method} {path}: {response.status_code}, expected {expected}")
        return body

    def body(self, prompt, selection=None):
        props = {"buyerId": self.buyer, "locale": "zh-CN", "currency": "CNY"}
        if selection:
            props["selectedSkill"] = selection
        return {"threadId": self.session, "runId": "audit-" + uuid.uuid4().hex,
                "messages": [{"id": uuid.uuid4().hex, "role": "user", "content": prompt}],
                "state": {}, "tools": [], "context": [], "forwardedProps": props}

    def run_agent(self, name, prompt, selection=None):
        body = self.body(prompt, selection)
        events = []
        started = time.monotonic()
        with self.client.stream("POST", "/commerce/ag-ui/run", json=body) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
        self.save(name + "-events.json", events)
        self.check(name + ":terminal", bool(events) and events[-1].get("type") == "RUN_FINISHED"
                   and events[-1].get("outcome", {}).get("type") == "success",
                   {"seconds": round(time.monotonic() - started, 2), "events": len(events),
                    "terminal": events[-1] if events else None})
        session = self.req("GET", f"/commerce/ag-ui/sessions/{self.session}")
        self.save(name + "-session.json", session)
        return events, session

    def crud(self):
        self.req("GET", "/health", buyer=False)
        catalog = self.req("GET", "/commerce/models", params={"session_id": self.session})
        self.selection = {k: catalog["selection"][k] for k in
                          ("profile_id", "profile_revision", "window_id", "thinking")}
        model_body = {"buyer_id": self.buyer, **self.selection,
                      "expected_revision": catalog["revision"]}
        updated = self.req("PATCH", f"/commerce/sessions/{self.session}/model",
                           buyer=False, json=model_body)
        self.check("model-selection", updated["revision"] > catalog["revision"])
        self.req("PATCH", f"/commerce/sessions/{self.session}/model", buyer=False,
                 json=model_body, expected=409)
        self.check("model-stale-revision-rejected", True)
        self.req("GET", "/commerce/models", params={"session_id": self.session,
                 "buyer_id": self.buyer + "-other"}, expected=403)
        self.check("session-owner-isolation", True, "demo 模式的归属检查，不等于真实身份认证")
        self.req("GET", "/commerce/context", params={"session_id": self.session})
        self.check("context-view", True, "只验证读取，未验证长上下文压缩效果")

        product = {"product_id": "P1049", "title": "合成验收收藏", "price": 39, "currency": "CNY"}
        saved = self.req("PUT", "/commerce/favorites/P1049", json={"product": product})
        self.check("favorite-write", any(p["product_id"] == "P1049" for p in saved["products"]))
        other = self.req("GET", "/commerce/favorites", params={"buyer_id": self.buyer + "-other"})
        self.check("favorite-isolation", not other["products"])
        self.req("PUT", "/commerce/favorites/P1049", expected=422,
                 json={"product": {**product, "product_id": "wrong"}})
        removed = self.req("DELETE", "/commerce/favorites/P1049")
        self.check("favorite-delete", not removed["products"])

        skill_body = {"title": "验收用澄清方案", "description": "合成数据，接手验收后删除",
                      "body": "用户要求表单时，用 show_shopping_form 澄清关键条件。不得代用户批准交易。"}
        self.skill = self.req("POST", "/commerce/my-skills", json=skill_body)["skill"]
        self.skill = self.req("PUT", "/commerce/my-skills/" + self.skill["id"],
                              json={**skill_body, "body": skill_body["body"] + "尊重预算和目的地。",
                                    "expected_version": self.skill["version"]})["skill"]
        self.check("personal-skill-version", str(self.skill["version"]) == "2")
        self.req("PUT", "/commerce/my-skills/" + self.skill["id"], expected=409,
                 json={**skill_body, "expected_version": "1"})
        self.check("personal-skill-stale-rejected", True)
        other = self.req("GET", "/commerce/my-skills", params={"buyer_id": self.buyer + "-other"})
        self.check("personal-skill-isolation", not other["skills"])
        self.req("POST", "/commerce/ag-ui/run", buyer=False, expected=422,
                 json=self.body("合成测试", {"id": self.skill["id"], "version": "2",
                    "contentHash": self.skill["content_hash"], "body": "不应接受客户端注入正文"}))
        self.check("selected-skill-extra-fields-rejected", True)
        self.req("POST", "/commerce/shopping-forms", expected=410, json={"session_id": self.session})
        self.check("deprecated-fixed-form-closed", True)

    def live_form(self):
        selected = {"id": self.skill["id"], "version": str(self.skill["version"]),
                    "contentHash": self.skill["content_hash"]}
        events, session = self.run_agent("skill-and-form",
            "我想买通勤背包。请现在调用 show_shopping_form，只生成三个必填问题："
            "budget 数字（人民币，最小1最大10000）、ship_to 文本、usage 单选（commute通勤或travel旅行）。"
            "不要搜索商品，不要替我填答案，展示后等待我提交。", selected)
        usages = session.get("state", {}).get("skillUsages", [])
        # 保留原始事件，以实际服务端 reading/used 回执为准。
        used = any(e.get("name") == "skill.preload" and e.get("value", {}).get("status") == "used"
                   for e in events)
        self.check("personal-skill-preload", used or any(u.get("status") == "used" for u in usages), usages)
        form = self.req("GET", "/commerce/shopping-forms", params={"session_id": self.session})["form"]
        self.check("dynamic-form-created", bool(form) and len(form.get("questions", [])) == 3)
        if not form:
            return
        answers = {}
        for q in form["questions"]:
            if q["type"] == "number":
                answers[q["id"]] = max(q.get("minimum") or 1, min(300, q.get("maximum") or 10000))
            elif q["type"] == "single_select":
                answers[q["id"]] = q["options"][0]["value"]
            elif q["type"] == "multi_select":
                answers[q["id"]] = [q["options"][0]["value"]]
            else:
                answers[q["id"]] = "CN"
        action = {"session_id": self.session, "expected_revision": form["revision"],
                  "request_id": "form-" + uuid.uuid4().hex, "version": "v0.9",
                  "action": {"name": "applyShoppingRequirements", "surfaceId": form["form_id"],
                    "sourceComponentId": "root", "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": {"requirements": answers}}}
        path = "/commerce/shopping-forms/" + form["form_id"] + "/actions"
        invalid = json.loads(json.dumps(action))
        invalid["action"]["context"]["requirements"]["unexpected"] = "invalid"
        self.req("POST", path, json=invalid, expected=422)
        first = self.req("POST", path, json=action)
        repeat = self.req("POST", path, json=action)
        self.check("form-submit-idempotent", first == repeat)
        self.req("POST", path, expected=409, json={**action, "request_id": "new-request"})
        self.check("form-stale-revision-rejected", True)
        _, restored = self.run_agent("form-followup", first["query"] + "\n请按以上答案推荐最多2款，必须查询当前目录，不要创建新表单，不要下单。")
        state = restored.get("state", {})
        self.check("form-followup-products", bool(state.get("products")),
                   {"product_count": len(state.get("products", []))})

    def memory(self):
        before = self.req("GET", "/commerce/preferences")
        response = self.client.post("/commerce/preferences", params={"buyer_id": self.buyer},
                                    json={"kind": "like", "statement": "喜欢轻便的通勤背包"})
        after = self.req("GET", "/commerce/preferences")
        self.save("memory.json", {"status": response.status_code, "response": response.json(),
                                  "before": before, "after": after})
        if response.status_code == 422 and "向量生成失败" in response.json().get("detail", "") and before == after:
            self.check("memory-dependency", True, response.json(), status="blocked")
            self.check("memory-failed-write-atomic", True)
        else:
            self.check("memory-write", response.status_code == 200, response.json())
            if response.status_code == 200:
                memory = after['preferences'][0]
                history = self.req('GET', f"/commerce/preferences/{memory['memory_id']}/history")
                self.check('memory-history', bool(history['events']))
                other = self.req('GET', '/commerce/preferences', params={'buyer_id': self.buyer + '-other'})
                self.check('memory-owner-isolation', not other['preferences'])
                edit = {'kind': 'like', 'statement': '喜欢轻便防水的通勤背包',
                        'memory_id': memory['memory_id'], 'expected_version': memory['version']}
                result = self.req('POST', '/commerce/preferences', json=edit)
                changed = next(p for p in result['preferences'] if p['memory_id'] == memory['memory_id'])
                self.check('memory-update-version', changed['version'] > memory['version'])
                self.req('POST', '/commerce/preferences', json=edit, expected=409)
                self.check('memory-stale-update-rejected', True)
                self.req('DELETE', '/commerce/preferences', json={
                    'statement': changed['statement'], 'memory_id': changed['memory_id'],
                    'expected_version': changed['version']})
                self.check('memory-delete', self.req('GET', '/commerce/preferences') == before)

    def automation(self):
        self.req("GET", "/commerce/automations/templates")
        self.req("GET", "/commerce/automations/options")
        schedule = {"kind": "once", "timezone": "Asia/Shanghai",
                    "at": (datetime.now() + timedelta(days=2)).replace(microsecond=0).isoformat()}
        preview = self.req("POST", "/commerce/automations/preview", buyer=False,
                           json={"buyer_id": self.buyer, "schedule": schedule})
        self.check("automation-preview", len(preview["times"]) == 1)
        definition = {"name": "接手验收合成任务", "prompt": "只回复：自动化执行成功。不要调用购物或交易工具。",
                      "schedule": schedule, "auto_start": False, "output_mode": "independent",
                      "model": self.selection, "currency": "CNY", "locale": "zh-CN"}
        create = {"buyer_id": self.buyer, "request_id": "save-audit", "definition": definition}
        self.task = self.req("POST", "/commerce/automations", buyer=False, json=create)
        repeat = self.req("POST", "/commerce/automations", buyer=False, json=create)
        self.check("automation-create-idempotent", self.task["id"] == repeat["id"])
        if not self.with_model:
            self.check("automation-real-execution", True, "手动执行会立即入队；需 --with-model", status="skipped")
            return
        command = {"buyer_id": self.buyer, "request_id": "manual-audit",
                   "expected_revision": self.task["revision"]}
        path = f"/commerce/automations/{self.task['id']}/runs"
        run = self.req("POST", path, buyer=False, json=command)
        same = self.req("POST", path, buyer=False, json=command)
        self.check("automation-manual-idempotent", run["id"] == same["id"])
        if self.with_model:
            # manual 本身即买家的显式启动，auto_start=False 只影响定时触发。
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                run = self.req("GET", f"/commerce/automation-runs/{run['id']}")
                if run["status"] not in {"queued", "starting", "running"}:
                    break
                time.sleep(2)
            self.check("automation-real-execution", run["status"] == "succeeded",
                       {"status": run["status"], "attempts": run.get("attempts"), "error": run.get("error")})
            if run["status"] == "succeeded":
                self.req("GET", f"/commerce/ag-ui/sessions/{run['session_id']}")

    def cleanup(self):
        if self.task:
            listing = self.req("GET", "/commerce/automations")
            current = next(t for t in listing["items"] if t["id"] == self.task["id"])
            result = self.req("POST", f"/commerce/automations/{current['id']}/actions", buyer=False,
                json={"buyer_id": self.buyer, "request_id": "archive-audit", "action": "archive",
                      "expected_revision": current["revision"]})
            self.check("automation-archived", result["status"] == "archived")
        if self.skill:
            self.req("DELETE", "/commerce/my-skills/" + self.skill["id"],
                     params={"expected_version": str(self.skill["version"])})
            self.check("personal-skill-cleanup", True)
        self.req("DELETE", "/commerce/favorites/P1049")

    def execute(self):
        try:
            self.crud()
            if self.with_model:
                self.live_form()
                self.memory()
            else:
                self.check("live-model-flows", True, "使用 --with-model 启用", status="skipped")
            self.automation()
        except Exception as error:
            self.check("runner-exception", False, {"type": type(error).__name__, "message": str(error)[:600]})
        finally:
            try:
                self.cleanup()
            except Exception as error:
                self.check("cleanup-exception", False, {"type": type(error).__name__, "message": str(error)[:600]})
            digest = hashlib.sha256()
            for path in sorted(Path("app").rglob("*.py")):
                digest.update(path.as_posix().encode())
                digest.update(path.read_bytes())
            summary = {"buyer": self.buyer, "session": self.session, "with_model": self.with_model,
                       "app_fingerprint_algorithm": "sorted app/**/*.py path UTF-8 + raw bytes",
                       "app_sha256": digest.hexdigest(), "counts": dict(Counter(r["status"] for r in self.results)),
                       "checks": self.results,
                       "scope": "本地补充诊断，不替代 harness、浏览器验收或生产验收"}
            self.save("summary.json", summary)
            self.client.close()
        return int(any(r["status"] == "fail" for r in self.results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--with-model", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path("eval/verification") / ("takeover-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    print(f"evidence: {output}", flush=True)
    raise SystemExit(Audit(args.base_url, output, args.with_model).execute())


if __name__ == "__main__":
    main()
