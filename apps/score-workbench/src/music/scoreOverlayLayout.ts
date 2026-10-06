/** All coordinates are CSS pixels relative to the score container's padding box. */
export function proposalOverlayLayout(page:{left:number;right:number;top:number},systemTop:number,left:number,right:number){
 const minLeft=page.left+8,maxRight=Math.max(minLeft+1,page.right-8);
 const start=Math.max(minLeft,Math.min(left,maxRight-1));
 const end=Math.max(start+1,Math.min(right,maxRight));
 // Keep the label (18px above the line) and its shadow inside the paper.
 return {left:start,width:end-start,top:Math.max(page.top+28,systemTop-12)};
}

export function overlayLabelOffset(markerLeft:number,labelWidth:number,pageLeft:number,pageRight:number){
 const width=Math.min(labelWidth,Math.max(1,pageRight-pageLeft-16));
 const left=Math.max(pageLeft+8,Math.min(markerLeft+2,pageRight-8-width));
 return {left:left-markerLeft,maxWidth:Math.max(1,pageRight-pageLeft-16)};
}
