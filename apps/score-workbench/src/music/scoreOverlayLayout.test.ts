import {expect,it} from 'vitest';
import {proposalOverlayLayout,overlayLabelOffset} from './scoreOverlayLayout';

it('keeps the first-system line and label inside the page',()=>{
 expect(proposalOverlayLayout({left:10,right:510,top:100},105,0,550)).toEqual({left:18,width:484,top:128});
});
it('preserves note endpoints and leaves a lane above later systems',()=>{
 expect(proposalOverlayLayout({left:10,right:510,top:100},300,80,400)).toEqual({left:80,width:320,top:288});
});
it('shifts long right-edge labels inward without moving their musical start',()=>{
 expect(overlayLabelOffset(460,120,10,510)).toEqual({left:-78,maxWidth:484});
 expect(overlayLabelOffset(80,120,10,510).left).toBe(2);
});
it('bounds labels on narrow pages',()=>{
 expect(overlayLabelOffset(70,200,0,100)).toEqual({left:-62,maxWidth:84});
});
