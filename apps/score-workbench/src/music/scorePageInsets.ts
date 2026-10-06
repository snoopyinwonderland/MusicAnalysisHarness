/** CSS pixels, relative to the SVG itself so repeated measurements do not accumulate padding. */
export function scorePageTopInset(inkTopFromSvg:number,clearance=40){
 return Number.isFinite(inkTopFromSvg)?Math.max(0,Math.ceil(clearance-inkTopFromSvg)):0;
}
