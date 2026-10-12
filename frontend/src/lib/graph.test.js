import test from "node:test";
import assert from "node:assert/strict";
import { canConnect, serializeGraph, imageSelection } from "./graph.js";
const nodes = [
  { id: "t", type: "text" },
  { id: "w", type: "workflow" },
  { id: "r", type: "result" },
  { id: "e", type: "workflow" },
];
test("preserves a deliberately chosen old image until a new result arrives", () => {
  const images = [
    { id: "old", created_at: "2026-10-12T01:00:00Z" },
    { id: "new", created_at: "2026-10-12T02:00:00Z" },
  ];
  const selected = { selectedAssetId: "old", latestSeenAssetId: "new" };
  assert.equal(imageSelection(selected, images).selectedAssetId, "old");
  assert.equal(
    imageSelection(selected, [...images, { id: "fresh" }]).selectedAssetId,
    "fresh",
  );
});
test("restores saved choices and handles generation completed while the page was closed", () => {
  const images = [
    { id: "old", created_at: "2026-10-12T01:00:00Z" },
    { id: "new", created_at: "2026-10-12T02:00:00Z" },
  ];
  assert.equal(
    imageSelection({ selectedAssetId: "old" }, images, "2026-10-12T03:00:00Z")
      .selectedAssetId,
    "old",
  );
  assert.equal(
    imageSelection({ selectedAssetId: "old" }, images, "2026-10-12T01:30:00Z")
      .selectedAssetId,
    "new",
  );
});
test("accepts matching ports, rejects invalid types and duplicate input", () => {
  const edge = { source: "t", target: "w", targetHandle: "text" };
  assert.equal(canConnect(edge, nodes, []), true);
  assert.equal(
    canConnect({ ...edge, targetHandle: "image" }, nodes, []),
    false,
  );
  assert.equal(canConnect(edge, nodes, [edge]), false);
});
test("rejects a cycle through an existing result node", () => {
  const edges = [{ source: "w", target: "r", targetHandle: "image" }];
  assert.equal(
    canConnect(
      { source: "r", target: "w", targetHandle: "image" },
      nodes,
      edges,
    ),
    false,
  );
  assert.equal(
    canConnect(
      { source: "r", target: "e", targetHandle: "image" },
      nodes,
      edges,
    ),
    true,
  );
});
test("saved graph excludes transient Vue Flow state and preserves choices", () => {
  const graph = serializeGraph(
    [
      {
        id: "r",
        type: "result",
        position: { x: 12, y: 23 },
        selected: true,
        dimensions: { width: 2 },
        data: { selectedAssetId: "old-image" },
      },
    ],
    [],
    { x: -12, y: 3, zoom: 0.7 },
    "manual",
  );
  assert.equal(graph.nodes[0].selected, undefined);
  assert.equal(graph.nodes[0].data.selectedAssetId, "old-image");
  assert.equal(graph.viewport.zoom, 0.7);
});
