import { t, tValue } from "../i18n/index";
import type { ProductCard } from "../types";
import { money, ProductImage } from "./ProductCards";
import Icon from "./Icon";
import { ProductImageCaption } from "./CatalogMedia";

export default function FavoritesList({ products, onDetail, onRemove, onBrowse }: {
  products: ProductCard[];
  onDetail: (product: ProductCard) => void;
  onRemove: (product: ProductCard) => void;
  onBrowse: () => void;
}) {
  return <section className="compact-favorites" aria-label={t("心选收藏")}>
    <div className="favorites-toolbar"><span>{tValue(products.length)}{t(" 件收藏")}</span><small>{t("收藏时的商品信息 · 下单前请重新核验价格与库存")}</small></div>
    {products.length ? <div className="favorite-list">{products.map(product => <article className="favorite-row" key={product.product_id}>
      <button className="favorite-thumbnail" aria-label={t("查看 {0} 详情", [product.title])} onClick={() => onDetail(product)}><ProductImage product={product} /></button>
      <div className="favorite-info"><button onClick={() => onDetail(product)}>{product.title}</button><span>{tValue(product.category)} · {tValue(product.brand)}</span><small><ProductImageCaption product={product} /></small></div>
      <div className="favorite-price"><strong>{tValue(money(product.price_major, product.currency))}</strong><small>{t("收藏时商品价")}</small></div>
      <div className="favorite-actions"><button onClick={() => onDetail(product)}>{t("查看详情")}</button><button aria-label={t("取消收藏 {0}", [product.title])} onClick={() => onRemove(product)}><Icon name="heart" />{t("取消收藏")}</button></div>
    </article>)}</div> : <div className="purchase-empty"><Icon name="heart" /><h2>{t("还没有收藏")}</h2><p>{t("点击商品上的爱心，把喜欢的好物留在这里。")}</p><button onClick={onBrowse}>{t("去发现好物")}</button></div>}
  </section>;
}
