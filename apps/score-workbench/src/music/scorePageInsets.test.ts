import {it,expect} from 'vitest';
import {scorePageTopInset} from './scorePageInsets';
it('reserves annotation space above protruding notation',()=>{
 expect(scorePageTopInset(-4)).toBe(44);expect(scorePageTopInset(28)).toBe(12);
});
it('preserves sufficient existing margins and handles missing measurements',()=>{
 expect(scorePageTopInset(75)).toBe(0);expect(scorePageTopInset(NaN)).toBe(0);
});
