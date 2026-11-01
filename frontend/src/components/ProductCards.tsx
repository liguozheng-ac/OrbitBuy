import { t, tValue, useLocale, getLocale } from "../i18n/index";
import { memo, useState } from "react";
import type { ProductCard } from "../types";
import Icon from "./Icon";
import { useProductMedia, ProductImageCaption, type MediaProduct } from "./CatalogMedia";
import "./compactProductCards.css";
export function money(value: number, currency: string) {
  if (!Number.isFinite(value)) return "待确认";
  try {
    return new Intl.NumberFormat(getLocale(), {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}
export function ProductImage({
  product,
  className = "",
}: {
  product: MediaProduct;
  className?: string;
}) {
  const media = useProductMedia(product);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  // 服务端注册表按精确 ID 补图，不从标题猜测；URL 更新后允许新图片重试。
  if (!media.url || failedUrl === media.url)
    return (
      <div className={`image-placeholder ${className}`}>
        <Icon name="bag" />
        <span>{tValue(product.category || t("好物详情"))}</span>
        <small>{t("暂未提供商品图片")}</small>
      </div>
    );
  if (media.cell !== undefined) return <svg className={`catalog-media-image ${className}`} viewBox="0 0 1 1" role="img" aria-label={tValue(media.alt)}>
    <image href={media.url} x={-(media.cell % 4)} y={-Math.floor(media.cell / 4)} width="4" height="4" onError={() => setFailedUrl(media.url)} />
  </svg>;
  return (
    <img
      className={className}
      src={media.url}
      alt={tValue(media.alt)}
      loading="lazy"
      onError={() => setFailedUrl(media.url)}
    />
  );
}
interface ProductCardsProps {
  products: ProductCard[];
  favoriteIds: Set<string>;
  comparedIds: Set<string>;
  onFavorite: (product: ProductCard) => void;
  onCompare: (product: ProductCard) => void;
  onDetail: (product: ProductCard) => void;
}
function ProductCards({
  products,
  favoriteIds,
  comparedIds,
  onFavorite,
  onCompare,
  onDetail,
}: ProductCardsProps) {
  useLocale();
  return (
    <div className="product-grid compact-product-grid">
      {products.map((product, index) => {
        const saved = favoriteIds.has(product.product_id),
          selected = comparedIds.has(product.product_id),
          rating = product.rating_summary;
        const primary = product.skus.find(
            (sku) => sku.sku_id === product.default_sku_id,
          ),
          landed = product.landed_price;
        return (
          <article
            className={`product-card ${selected ? "selected" : ""}`}
            key={product.product_id}
            style={{ animationDelay: `${Math.min(index, 5) * 55}ms` }}
          >
            <div className="product-visual">
              <button
                className="image-open"
                onClick={() => onDetail(product)}
                aria-label={t("查看 {0} 详情", [product.title])}
              >
                <ProductImage product={product} />
              </button>
              <span className="product-badge">{tValue(product.category)}</span>
              <button
                className={`heart ${saved ? "saved" : ""}`}
                onClick={() => onFavorite(product)}
                aria-label={`${saved ? t("取消收藏") : t("收藏")} ${product.title}`}
                aria-pressed={saved}
              >
                <Icon name="heart" />
              </button>
              <span className="visual-caption">
                <ProductImageCaption product={product} />
              </span>
            </div>
            <div className="product-body">
              <div className="product-topline">
                <span>{tValue(product.brand || t("精选商品"))}</span>
                {rating && (
                  <span className="rating">
                    <i>★</i> {tValue(rating.average.toFixed(1))}{tValue(" ")}
                    <span>({tValue(rating.review_count)}{tValue(product.rating_is_live ? "" : t(" · 样例"))})</span>
                  </span>
                )}
              </div>
              <button
                className="product-title"
                onClick={() => onDetail(product)}
              >
                {product.title}
              </button>
              <div className="product-subtitle">
                {primary?.spec || product.highlights[0] || t("查看商品详细信息")}
              </div>
              <div className="product-price-row">
                <div className="price">
                  {tValue(money(product.price_major, product.currency))}
                </div>
                <span className="price-kind">{t("商品价")}</span>
              </div>
              {landed &&
              !landed.unavailable_reason &&
              Number.isFinite(landed.landed_total_major) ? (
                <div className="card-landed">
                  {t("到手价")}{tValue(money(landed.landed_total_major, landed.currency))}
                  <span>{t("配送至 ")}{tValue(landed.ship_to)}{t(" · 默认规格")}</span>
                </div>
              ) : (
                <div className="card-landed pending">
                  {t("到手价待目的地与规格确认")}</div>
              )}
              <div className="product-footer">
                <label className="compare-check">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onCompare(product)}
                    aria-label={t("将 {0} 加入比较", [product.title])}
                  />
                  {t("加入比较")}</label>
                <button
                  className="detail-button"
                  onClick={() => onDetail(product)}
                >
                  {t("看看细节")}<Icon name="arrow" />
                </button>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

// 商品引用与交互回调不变时，不随助手逐字输出重绘商品区域。
export default memo(ProductCards);
