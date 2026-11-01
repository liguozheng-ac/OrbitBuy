# -*- coding: utf-8 -*-
"""本轮商品投影：仅明确多商品 ID 的精确查询可跨工具结果合并。"""
from __future__ import annotations

import copy
import re
import json

_IDENTIFIER = re.compile(r"(?<![A-Za-z0-9])P\d{4,}(?:-S\d+)?(?![A-Za-z0-9-])")


class ProductCandidateProjection:
    def __init__(self, raw_query: str):
        self.identifiers = list(dict.fromkeys(_IDENTIFIER.findall(raw_query.upper())))
        self._product_order = list(dict.fromkeys(identifier.split("-S", 1)[0] for identifier in self.identifiers))
        self._merge_exact = len(self._product_order) > 1
        self._cards: dict[str, dict] = {}
        self._references: dict[str, list[str]] = {}
        self.has_result = False
        self.result: dict | None = None
        self._conditions: str | None = None
        limits = re.findall(r"(?:最多|至多|推荐|寻找|找|返回|展示)\s*(\d+)\s*(?:款|件|个)|(?:up to|at most|no more than)\s+(\d+)\b|最大\s*(\d+)\s*(?:点|件|個)", raw_query, re.I)
        values = {int(next(v for v in match if v)) for match in limits}
        self.limit = next(iter(values)) if len(values) == 1 and 1 <= next(iter(values)) <= 50 else None

    def _display(self, result: dict) -> dict:
        if self.limit is not None:
            result['hits'] = result['hits'][:self.limit]
            result['hit_count'] = len(result['hits'])
            result['display_limit'] = self.limit
        return result

    def _rank(self, card):
        product = card["product_id"].upper()
        identifiers = [identifier for identifier in self.identifiers if identifier.split("-S", 1)[0] == product]
        specific = [identifier for identifier in identifiers if "-S" in identifier]
        # 指定 SKU 时不能把同商品默认 SKU 的价格和图片口径冒充为请求的规格。
        if specific:
            selected = card.get("default_sku_id", "").upper()
            return self.identifiers.index(selected) if selected in specific else None
        return self.identifiers.index(product) if product in identifiers else None

    def apply(self, payload: dict) -> bool:
        """只消费完整 product_search_tool.result；无命中信息的错误不伪装成空检索。"""
        if not isinstance(payload, dict) or payload.get("tool") != "product_search_tool":
            return False
        hits = payload.get("hits")
        if not isinstance(hits, list) or any(not isinstance(card, dict) or not isinstance(card.get("product_id"), str) for card in hits):
            return False
        self.has_result = True
        result = copy.deepcopy(payload)
        result.pop("tool", None)
        conditions = payload.get("query_conditions", {})
        # 比较中的精确 ID 可以不同，但预算、目的国及其它资格必须同口径。
        signature = json.dumps({k: v for k, v in conditions.items() if k not in
            {"normalized_query", "product_id", "sku_id", "top_k"}}, sort_keys=True, ensure_ascii=False)
        if self._conditions is not None and self._conditions != signature:
            self._cards.clear()
            self._references.clear()
        self._conditions = signature
        if not self._merge_exact or payload.get("recall_strategy") != "exact_id_lookup" or not hits:
            # 普通检索、改条件和空结果一律替换；不能继承另一阶段或另一轮的候选。
            self._cards.clear()
            self._references.clear()
            self.result = self._display(result)
            return True

        accepted = [card for card in hits if self._rank(card) is not None]
        if not accepted:
            self._cards.clear()
            self._references.clear()
        for rejected in payload.get("filtered_out", []):
            if isinstance(rejected, dict):
                product = str(rejected.get("product_id", "")).upper()
                self._cards.pop(product, None)
                self._references.pop(product, None)
        refs = [ref for ref in [payload.get("result_ref"), *payload.get("result_refs", [])] if isinstance(ref, str) and ref]
        for card in accepted:
            product = card["product_id"].upper()
            old = self._cards.get(product)
            if old is not None and self._rank(old) < self._rank(card):
                continue
            self._cards[product] = copy.deepcopy(card)
            self._references[product] = list(dict.fromkeys(refs))
        ordered = [product for product in self._product_order if product in self._cards]
        result["hits"] = [copy.deepcopy(self._cards[product]) for product in ordered]
        result["hit_count"] = len(ordered)
        result["total_candidates"] = len(ordered)
        result["requested_identifiers"] = list(self.identifiers)
        result["result_refs"] = list(dict.fromkeys(ref for product in ordered for ref in self._references.get(product, [])))
        # 合并结果没有单个原工具引用能代表全部事实，不能误指最后完成的那张卡。
        result.pop("result_ref", None)
        if len(result["result_refs"]) == 1:
            result["result_ref"] = result["result_refs"][0]
        self.result = self._display(result)
        return True
