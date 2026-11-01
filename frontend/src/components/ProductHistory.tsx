import { t, tValue , getLocale } from "../i18n/index";
import { ProductImageCaption } from "./CatalogMedia";
import type { CommerceSnapshot } from "../types";
import { money, ProductImage } from "./ProductCards";

/** 历史报价只读展示，不能用旧库存、旧金额直接发起交易。 */
export default function ProductHistory({batches = []}: {batches: CommerceSnapshot["productHistory"]}) {
  if (!batches.length) return null;
  return <details className="historical-products">
    <summary>{t("历史商品记录 · ")}{tValue(batches.length)}{t(" 轮")}</summary>
    <p className="results-footnote">{t("以下为当时保存的商品信息。价格、库存和配送条件可能变化，继续购买前请重新核验。")}</p>
    {batches.map(batch => <section key={batch.runId} aria-label={t("历史商品批次")}>
      <h3>{tValue(new Date(batch.updatedAt).toLocaleString(getLocale()))} · {tValue(batch.products.length)}{t(" 件")}</h3>
      <div className="product-grid">{batch.products.map((product, index) => <article className="product-card" key={product.product_id}>
        <div className="product-visual"><ProductImage product={product}/>
          <span className="visual-caption"><ProductImageCaption product={product} /></span>
        </div>
        <div className="product-body">
          <h4>{tValue(index + 1)}. {product.title}</h4>
          <p>{t("当时商品价：")}{tValue(money(product.price_major, product.currency))}</p>
          {product.landed_price && <p>{t("当时报价：")}{tValue(product.landed_price.unavailable_reason || money(product.landed_price.landed_total_major, product.landed_price.currency))}{t(" · 配送至 ")}{tValue(product.landed_price.ship_to)}</p>}
          <ul>{product.skus.map(sku => <li key={sku.sku_id}>{sku.spec} · {tValue(money(sku.price_major, sku.currency))}{t(" · 当时库存 ")}{tValue(sku.stock)} · {tValue(sku.sku_id)}</li>)}</ul>
        </div>
      </article>)}</div>
    </section>)}
  </details>;
}
