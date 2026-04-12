import React, { useRef, useEffect } from 'react';
import { createRoot, Root } from 'react-dom/client';
import { GraphicWalker, getComputation, exportFullRaw } from '@kanaries/graphic-walker';
import '@kanaries/graphic-walker/dist/style.css';
import type { IMutField, IRow } from '@kanaries/graphic-walker';
import type { VizSpecStore } from '@kanaries/graphic-walker';

interface GWRenderState {
  root: Root | null;
  storeRef: React.RefObject<VizSpecStore | null> | null;
}

const state: GWRenderState = {
  root: null,
  storeRef: null,
};

function GWApp({
  data,
  fields,
  savedSpecs,
  onStoreReady,
}: {
  data: IRow[];
  fields: IMutField[];
  savedSpecs?: any[];
  onStoreReady: (ref: React.RefObject<VizSpecStore | null>) => void;
}) {
  const computation = getComputation(data);
  const storeRef = useRef<VizSpecStore | null>(null);

  useEffect(() => {
    onStoreReady(storeRef);
  }, []);

  return (
    <div style={{ width: '100%', minHeight: '500px' }}>
      <GraphicWalker
        data={data}
        rawFields={fields}
        computation={computation}
        storeRef={storeRef}
        chart={savedSpecs}
        themeKey="g2"
        appearance="light"
        dark="media"
      />
    </div>
  );
}

function render(
  container: HTMLElement,
  data: IRow[],
  rawFields: any[],
  savedSpecs?: any[]
) {
  const fields: IMutField[] = rawFields.map((f) => ({
    fid: f.fid,
    key: f.fid,
    name: f.name || f.fid,
    analyticType: f.analyticType || 'dimension',
    semanticType: f.semanticType || 'nominal',
    basename: f.name || f.fid,
    path: undefined as any,
  }));

  if (state.root) {
    state.root.unmount();
  }

  state.root = createRoot(container);
  state.root.render(
    <GWApp
      data={data}
      fields={fields}
      savedSpecs={savedSpecs}
      onStoreReady={(ref) => {
        state.storeRef = ref;
      }}
    />
  );
}

function getSpecs(): string[] | null {
  if (!state.storeRef?.current) {
    console.warn('[GraphicWalkerCKAN] Store not ready');
    return null;
  }
  const store = state.storeRef.current;
  try {
    return store.visList.map((vis: any) => exportFullRaw(vis));
  } catch (e) {
    console.error('[GraphicWalkerCKAN] Failed to export specs:', e);
    return null;
  }
}

function getSpecsNow(): any[] | null {
  if (!state.storeRef?.current) {
    return null;
  }
  const store = state.storeRef.current;
  return store.visList.map((vis: any) => vis.now);
}

// Expose to global scope for CKAN template
(window as any).GraphicWalkerCKAN = {
  render,
  getSpecs,
  getSpecsNow,
};

export { render, getSpecs, getSpecsNow };
