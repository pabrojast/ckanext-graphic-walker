import React from 'react';
import { createRoot, Root } from 'react-dom/client';
import { GraphicWalker } from '@kanaries/graphic-walker';
import '@kanaries/graphic-walker/dist/style.css';
import { getComputation } from '@kanaries/graphic-walker';
import type { IMutField, IRow } from '@kanaries/graphic-walker';

interface GWRenderState {
  root: Root | null;
}

const state: GWRenderState = {
  root: null,
};

function GWApp({ data, fields }: { data: IRow[]; fields: IMutField[] }) {
  const computation = getComputation(data);

  return (
    <div style={{ width: '100%', minHeight: '500px' }}>
      <GraphicWalker
        data={data}
        rawFields={fields}
        computation={computation}
        themeKey="g2"
        appearance="light"
        dark="media"
      />
    </div>
  );
}

function render(container: HTMLElement, data: IRow[], rawFields: any[]) {
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
  state.root.render(<GWApp data={data} fields={fields} />);
}

// Expose to global scope for CKAN template
(window as any).GraphicWalkerCKAN = {
  render,
};

export { render };
