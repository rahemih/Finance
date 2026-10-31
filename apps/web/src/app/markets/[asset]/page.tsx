import { notFound } from "next/navigation";
import { AssetPreview } from "../../../components/markets/markets-preview";
export const metadata = {title:"NEXUS QUANT — نمای دارایی (پیش‌نمایش)",robots:{index:false,follow:false}};
/**
 * Only the explicit sandbox fixture is renderable until Domain-owned canonical
 * Asset Registry + auth/data contracts are connected. Unknown IDs fail closed.
 */
export default async function Page({params}:{params:Promise<{asset:string}>}){
 const {asset}=await params;
 if(asset!=="mock-btcusdt") notFound();
 return <AssetPreview/>;
}
