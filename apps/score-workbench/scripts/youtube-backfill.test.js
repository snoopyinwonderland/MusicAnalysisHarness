import {describe,expect,it} from 'vitest';
import {arrangementIdentity,candidateEligibility,candidateRelevance,composerRelevance,normalizeComposer,normalizeWorkTitle,titleRelevance} from './youtube-backfill.mjs';

describe('YouTube title and composer matching',()=>{
 it('rejects an unrelated hymn that merely shares a generic title',()=>{
  const result=candidateRelevance('Always With Me','Composed by Joe Hisaishi\nArranged by Reflet des Nuages','예수, 늘 함께 하시네 - 마커스워십 (Official) | Jesus, always with me','MARKERS WORSHIP');
  expect(result.title.accepted).toBe(true);
  expect(result.composer.accepted).toBe(false);
  expect(result.accepted).toBe(false);
 });
 it('accepts the work title together with its composer',()=>{
  const result=candidateRelevance('Always With Me','Joe Hisaishi','Always With Me - Spirited Away / Joe Hisaishi','Joe Hisaishi Collection');
  expect(result.accepted).toBe(true);
  expect(result.composer.coverage).toBe(1);
 });
 it('accepts a licensed recording when composer credit is in the video description',()=>{
  const result=candidateRelevance('Always With Me','Joe Hisaishi','Always With Me (from "Spirited Away")','Rozen - Topic','Composer: Joe Hisaishi Arranger: ROZEN');
  expect(result.accepted).toBe(true);
 });
 it('keeps title-only matching for records without reliable composer metadata',()=>{
  expect(candidateRelevance('Caro Mio Ben','','Caro Mio Ben - piano accompaniment','Music Archive').accepted).toBe(true);
  expect(titleRelevance('Caro Mio Ben','Caro Mio Ben - piano accompaniment').accepted).toBe(true);
  expect(composerRelevance('Unknown','anything').required).toBe(false);
  expect(normalizeComposer('Composed by Joe Hisaishi\nArranged by Someone')).toBe('Joe Hisaishi');
 });
 it('rejects clips under 90 seconds and hashtag spam even when the title matches',()=>{
  const video=(title,duration,description='Official music')=>({snippet:{title,channelTitle:'Music channel',description},contentDetails:{duration}});
  expect(candidateEligibility('Hakuna Matata','Elton John',video('Hakuna Matata - Elton John','PT12S')).accepted).toBe(false);
  expect(candidateEligibility('Hakuna Matata','Elton John',video('Hakuna Matata #shortvideo #viral - Elton John','PT4M2S')).accepted).toBe(false);
  expect(candidateEligibility('Hakuna Matata','Elton John',video('Elton John - Hakuna Matata (Official Audio)','PT4M2S')).accepted).toBe(true);
 });
 it('removes numbered file prefixes without deleting numbers that belong to titles',()=>{
  expect(normalizeWorkTitle('3. A Whole New World, Piano Solo.musicxml.xml')).toBe('A Whole New World');
  expect(normalizeWorkTitle('10,000 Hours.xml')).toBe('10 000 Hours');
  expect(normalizeWorkTitle('13 Jours en France.xml')).toBe('13 Jours en France');
  expect(normalizeWorkTitle('2 Become 1.xml')).toBe('2 Become 1');
 });
 it('shares one representative lookup across solo, duet, trio, and quartet arrangements',()=>{
  const composer='Composed by Alan Menken\nArranged by Reflet des Nuages';
  expect(arrangementIdentity('A Whole New World, Piano Solo',composer)).toBe(arrangementIdentity('A Whole New World, Violin and Piano Duet',composer));
  expect(arrangementIdentity('A Whole New World, Piano Solo',composer)).toBe(arrangementIdentity('A Whole New World, Violin, Cello and Piano Trio',composer));
  expect(arrangementIdentity('A Whole New World, Piano Solo',composer)).toBe(arrangementIdentity('A Whole New World, Violin, Cello, Contrabass and Piano Quartet',composer));
 });
});
