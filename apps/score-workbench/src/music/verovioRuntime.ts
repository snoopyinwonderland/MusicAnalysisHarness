import type { VerovioToolkit } from 'verovio/esm';

let runtime: Promise<{ module: unknown; esm: typeof import('verovio/esm') }> | null = null;

export const newVerovioToolkit = async (): Promise<VerovioToolkit> => {
  runtime ??= Promise.all([import('verovio/wasm'), import('verovio/esm')]).then(async ([wasm, esm]: any[]) => ({ module: await wasm.default(), esm }));
  const { module, esm } = await runtime;
  return new esm.VerovioToolkit(module as never);
};
