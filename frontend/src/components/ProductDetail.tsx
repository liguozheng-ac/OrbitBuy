import { t, tValue } from "../i18n/index";
import { useState } from "react";
import type { ProductCard } from "../types";
import Icon from "./Icon";
import { ProductImageCaption } from "./CatalogMedia";
import Modal from "./Modal";
import { money, ProductImage } from "./ProductCards";
import "./productDetail.css";

export default function ProductDetail({
  product,
  busy,
  onClose,
  onCompare,
  onAsk,
  onPrepare,
}: {
  product: ProductCard;
  busy: boolean;
  onClose: () => void;
  onCompare: (product: ProductCard) => void;
  onAsk: (query: string) => void;
  onPrepare: (product: ProductCard, skuId: string) => void;
}) {
  const [skuId, setSkuId] = useState(
    product.default_sku_id || product.skus[0]?.sku_id || "",
  );
  const sku = product.skus.find((item) => item.sku_id === skuId),
    landed = product.landed_price;
  const canShowLanded =
    skuId === product.default_sku_id &&
    landed &&
    !landed.unavailable_reason &&
    Number.isFinite(landed.landed_total_major);
  return (
    <Modal title={t("{0} 商品详情", [product.title])} drawer onClose={onClose}>
      <section className="product-detail" aria-label={t("商品信息与规格")}>
        <div className="detail-heading">{t("商品详情")}</div>
        <div className="detail-summary">
          <figure className="detail-image">
            <div className="detail-thumbnail">
              <ProductImage product={product} />
            </div>
            <figcaption>
              <ProductImageCaption product={product} />
            </figcaption>
          </figure>
          <div className="detail-summary-copy">
            <div className="detail-brand">{tValue(product.brand || product.category)}</div>
            <h2>{product.title}</h2>
            <div className="detail-price-row">
              <strong className="detail-price">
                {tValue(money(sku?.price_major ?? product.price_major, sku?.currency ?? product.currency))}
              </strong>
              <span className="detail-price-kind">{t("当前规格商品价")}</span>
            </div>
          </div>
        </div>
        <p className="detail-description">
          {product.description || product.highlights.join("；")}
        </p>
        {product.skus.length > 0 && (
          <fieldset className="sku-picker">
            <legend>{t("选择规格")}</legend>
            {product.skus.map((item) => (
              <label
                key={item.sku_id}
                className={skuId === item.sku_id ? "chosen" : ""}
              >
                <input
                  type="radio"
                  name="product-sku"
                  value={item.sku_id}
                  checked={skuId === item.sku_id}
                  onChange={() => setSkuId(item.sku_id)}
                />
                <span>{item.spec}</span>
                <small>
                  {tValue(item.stock > 0 ? t("目录库存 {0}", [item.stock]) : t("目录暂无库存"))}
                </small>
              </label>
            ))}
          </fieldset>
        )}
        <dl className="detail-specs">
          <div>
            <dt>{t("商品编号")}</dt>
            <dd>{tValue(product.product_id)}</dd>
          </div>
          {sku && (
            <div>
              <dt>{t("规格编号")}</dt>
              <dd>{tValue(sku.sku_id)}</dd>
            </div>
          )}
          <div>
            <dt>{t("商品分类")}</dt>
            <dd>{tValue(product.category)}</dd>
          </div>
          <div>
            <dt>{t("原产地")}</dt>
            <dd>{tValue(product.origin_country || t("未提供"))}</dd>
          </div>
          {(product.ships_to?.length ?? 0) > 0 && (
            <div>
              <dt>{t("配送地区")}</dt>
              <dd>{tValue(product.ships_to?.join(" / "))}</dd>
            </div>
          )}
          {product.rating_summary && (
            <div>
              <dt>{tValue(product.rating_is_live ? t("商品评分") : t("评分样例"))}</dt>
              <dd>
                ★ {tValue(product.rating_summary.average)} ·{tValue(" ")}
                {tValue(product.rating_summary.review_count)} {t("条")}</dd>
            </div>
          )}
        </dl>
        {canShowLanded ? (
          <div className="landed-detail-panel">
            <strong>
              {t("到手价")}{tValue(money(landed.landed_total_major, landed.currency))}
            </strong>
            <span>
              {t("小计")}{tValue(money(landed.subtotal_major, landed.currency))}{t(" + 运费")}{tValue(" ")}
              {tValue(money(landed.freight_major, landed.currency))}{t(" + 关税")}{tValue(" ")}
              {tValue(money(landed.tariff_major, landed.currency))}
            </span>
            <small>{t("配送至 ")}{tValue(landed.ship_to)}{t(" · 对应当前默认规格报价")}</small>
          </div>
        ) : (
          <p className="detail-quote-note" role="status">
            {tValue(skuId !== product.default_sku_id
    ? t("已更换规格，到手价需重新查询。") : landed?.unavailable_reason || t("到手价待目的地与规格确认。"))}
          </p>
        )}
        <p className="detail-note">
          {t("价格、库存为目录查询结果，购买前需要再次核对。图片与评分如标注为示意或样例，不代表实时平台信息。")}</p>
        <div className="detail-actions">
          <button
            className="detail-verify"
            disabled={busy}
            onClick={() => {
              onAsk(
                `请进一步核对「${product.title}」（product_id=${product.product_id}${sku ? `，sku_id=${sku.sku_id}，规格=${sku.spec}` : ""}）的当前库存与到手价。`,
              );
              onClose();
            }}
          >
            <Icon name="chat" />
            {tValue(busy ? t("正在处理中") : t("核验库存与报价"))}
          </button>
          <button
            className="detail-prepare"
            disabled={busy || !sku || sku.stock <= 0}
            onClick={() => sku && onPrepare(product, sku.sku_id)}
          >
            {t("准备下单意向")}</button>
          <button
            className="detail-compare"
            aria-label={t("用当前规格比较")}
            onClick={() =>
              onCompare(
                sku
                  ? {
                      ...product,
                      default_sku_id: sku.sku_id,
                      price_major: sku.price_major,
                      currency: sku.currency,
                      landed_price: canShowLanded ? landed : undefined,
                    }
                  : product,
              )
            }
          >
            <Icon name="compare" />
            {t("比较")}</button>
        </div>
      </section>
    </Modal>
  );
}
