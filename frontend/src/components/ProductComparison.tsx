import { t, tValue } from "../i18n/index";
import type { ProductCard } from "../types";
import Modal from "./Modal";
import { money, ProductImage } from "./ProductCards";
export default function ProductComparison({
  products,
  onClose,
}: {
  products: ProductCard[];
  onClose: () => void;
}) {
  return (
    <Modal title={t("商品比较")} onClose={onClose}>
      <h2>{t("放在一起，选择更清楚。")}</h2>
      <p className="modal-intro">{t("关注你在意的不同，也给决定留一点空间。")}</p>
      <div className="comparison-scroll">
        <table className="compare-table">
          <thead>
            <tr>
              <th>{t("你的心选")}</th>
              {products.map((product) => (
                <th key={product.product_id}>
                  <ProductImage product={product} />
                  <strong>{product.title}</strong>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{t("商品价")}</td>
              {products.map((p) => (
                <td key={p.product_id}>
                  <span className="compare-price">
                    {tValue(money(p.price_major, p.currency))}
                  </span>
                </td>
              ))}
            </tr>
            <tr>
              <td>{t("报价规格")}</td>
              {products.map((p) => (
                <td key={p.product_id}>
                  {p.skus.find((sku) => sku.sku_id === p.default_sku_id)
    ?.spec || t("目录默认规格")}
                </td>
              ))}
            </tr>
            <tr>
              <td>{t("分类")}</td>
              {products.map((p) => (
                <td key={p.product_id}>{tValue(p.category)}</td>
              ))}
            </tr>
            <tr>
              <td>{t("商品特点")}</td>
              {products.map((p) => (
                <td key={p.product_id}>
                  {tValue(p.highlights.slice(0, 3).join("；") || t("目录未提供"))}
                </td>
              ))}
            </tr>
            <tr>
              <td>{t("可选规格")}</td>
              {products.map((p) => (
                <td key={p.product_id}>
                  {p.skus.map((s) => s.spec).join(" / ") || t("目录未提供")}
                </td>
              ))}
            </tr>
            <tr>
              <td>{t("评分样例")}</td>
              {products.map((p) => (
                <td key={p.product_id}>
                  {tValue(p.rating_summary
    ? t("★ {0}（{1} 条）", [p.rating_summary.average, p.rating_summary.review_count]) : t("未提供"))}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="drawer-note comparison-note">
        {t("基于当前查看的目录快照比较。不同规格、配送地区与币种可能影响最终价格；未提供的信息不做推断。")}</p>
    </Modal>
  );
}
