export type RasterFormat = 'png' | 'jpg';
export type RasterizedSvg = { blob: Blob; width: number; height: number };
export type JpegPdfPage = { bytes: Uint8Array; width: number; height: number };

const MAX_CANVAS_SIDE = 16384;
const MAX_CANVAS_AREA = 48_000_000;

export const svgPixelDimensions = (svg: string) => {
  const root = svg.match(/<svg\b[^>]*>/i)?.[0] || '', widthAttr = root.match(/\bwidth="([\d.]+)(?:px)?"/i), heightAttr = root.match(/\bheight="([\d.]+)(?:px)?"/i), viewBox = root.match(/\bviewBox="[\d.-]+\s+[\d.-]+\s+([\d.]+)\s+([\d.]+)"/i);
  const viewWidth = Number(viewBox?.[1]) || 0, viewHeight = Number(viewBox?.[2]) || 0;
  let width = Number(widthAttr?.[1]) || viewWidth, height = Number(heightAttr?.[1]) || viewHeight;
  if (!width || !height) throw new Error('SVG의 출력 크기를 확인할 수 없습니다.');
  const fit = Math.min(1, MAX_CANVAS_SIDE / width, MAX_CANVAS_SIDE / height, Math.sqrt(MAX_CANVAS_AREA / (width * height)));
  width = Math.max(1, Math.floor(width * fit)); height = Math.max(1, Math.floor(height * fit));
  return { width, height, limited: fit < 1 };
};

const canvasBlob = (canvas: HTMLCanvasElement, type: string, quality?: number) => new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('이미지 인코딩에 실패했습니다.')), type, quality));

export const rasterizeSvg = async (svg: string, format: RasterFormat, quality = 0.94): Promise<RasterizedSvg> => {
  const { width, height } = svgPixelDimensions(svg), url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })), image = new Image();
  try {
    image.decoding = 'async';
    await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error('SVG를 이미지로 불러오지 못했습니다.')); image.src = url; });
    const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
    const context = canvas.getContext('2d'); if (!context) throw new Error('Canvas를 만들 수 없습니다.');
    if (format === 'jpg') { context.fillStyle = '#ffffff'; context.fillRect(0, 0, width, height); }
    context.drawImage(image, 0, 0, width, height);
    return { blob: await canvasBlob(canvas, format === 'png' ? 'image/png' : 'image/jpeg', format === 'jpg' ? quality : undefined), width, height };
  } finally { URL.revokeObjectURL(url); }
};

const encoder = new TextEncoder();
const ascii = (value: string) => encoder.encode(value);
const concatBytes = (chunks: readonly Uint8Array[]) => {
  const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0), output = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { output.set(chunk, offset); offset += chunk.length; }
  return output;
};
const points = (pixels: number) => Math.max(1, Math.round(pixels * 0.75 * 100) / 100);

export const buildJpegPdf = (pages: readonly JpegPdfPage[]) => {
  if (!pages.length) throw new Error('PDF에 넣을 이미지가 없습니다.');
  const chunks: Uint8Array[] = [], offsets: number[] = [], objectCount = 2 + pages.length * 3; let length = 0;
  const push = (chunk: Uint8Array) => { chunks.push(chunk); length += chunk.length; };
  const pushText = (value: string) => push(ascii(value));
  const beginObject = (id: number) => { offsets[id] = length; pushText(`${id} 0 obj\n`); };
  const endObject = () => pushText('endobj\n');

  push(new Uint8Array([0x25,0x50,0x44,0x46,0x2d,0x31,0x2e,0x34,0x0a,0x25,0xe2,0xe3,0xcf,0xd3,0x0a]));
  beginObject(1); pushText('<< /Type /Catalog /Pages 2 0 R >>\n'); endObject();
  beginObject(2); pushText(`<< /Type /Pages /Count ${pages.length} /Kids [${pages.map((_,index)=>`${3+index*3} 0 R`).join(' ')}] >>\n`); endObject();
  pages.forEach((page,index) => {
    const pageId=3+index*3,imageId=pageId+1,contentId=pageId+2,width=points(page.width),height=points(page.height),content=`q\n${width} 0 0 ${height} 0 0 cm\n/Im0 Do\nQ\n`,contentBytes=ascii(content);
    beginObject(pageId); pushText(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << /XObject << /Im0 ${imageId} 0 R >> >> /Contents ${contentId} 0 R >>\n`); endObject();
    beginObject(imageId); pushText(`<< /Type /XObject /Subtype /Image /Width ${page.width} /Height ${page.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${page.bytes.length} >>\nstream\n`); push(page.bytes); pushText('\nendstream\n'); endObject();
    beginObject(contentId); pushText(`<< /Length ${contentBytes.length} >>\nstream\n`); push(contentBytes); pushText('endstream\n'); endObject();
  });
  const xrefOffset=length; pushText(`xref\n0 ${objectCount+1}\n0000000000 65535 f \n`);
  for(let id=1;id<=objectCount;id++)pushText(`${String(offsets[id]).padStart(10,'0')} 00000 n \n`);
  pushText(`trailer\n<< /Size ${objectCount+1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`);
  return concatBytes(chunks);
};

export const pdfFromSvgPages = async (svgs: readonly string[]) => {
  const pages: JpegPdfPage[] = [];
  for (const svg of svgs) {
    const raster = await rasterizeSvg(svg, 'jpg', 0.95);
    pages.push({ bytes: new Uint8Array(await raster.blob.arrayBuffer()), width: raster.width, height: raster.height });
  }
  return new Blob([buildJpegPdf(pages) as BlobPart], { type: 'application/pdf' });
};

export const downloadBlobFile = (blob: Blob, filename: string) => {
  const url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;anchor.download=filename;anchor.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
};
