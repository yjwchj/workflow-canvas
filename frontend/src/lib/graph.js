export const emptyGraph = () => ({
  nodes: [],
  edges: [],
  viewport: { x: 0, y: 0, zoom: 1 },
  selectionMode: "manual",
});

export function imageSelection(data, images, savedAt) {
  const last = images.at(-1);
  if (!last) return data;
  const hasSavedChoice = images.some(
    (image) => image.id === data.selectedAssetId,
  );
  const unseen = data.latestSeenAssetId
    ? data.latestSeenAssetId !== last.id
    : !savedAt || Date.parse(last.created_at) > Date.parse(savedAt);
  return {
    ...data,
    selectedAssetId: !hasSavedChoice || unseen ? last.id : data.selectedAssetId,
    latestSeenAssetId: last.id,
  };
}
export function canConnect(connection, nodes, edges) {
  const source = nodes.find((n) => n.id === connection.source);
  const target = nodes.find((n) => n.id === connection.target);
  if (!source || !target || source.id === target.id) return false;
  const handle = connection.targetHandle;
  const valid =
    (source.type === "text" &&
      target.type === "workflow" &&
      handle === "text") ||
    (["image", "result"].includes(source.type) &&
      target.type === "workflow" &&
      handle === "image") ||
    (source.type === "workflow" &&
      target.type === "result" &&
      handle === "image");
  if (
    !valid ||
    edges.some((e) => e.target === target.id && e.targetHandle === handle)
  )
    return false;
  const stack = [target.id],
    seen = new Set();
  while (stack.length) {
    const id = stack.pop();
    if (id === source.id) return false;
    if (seen.has(id)) continue;
    seen.add(id);
    stack.push(...edges.filter((e) => e.source === id).map((e) => e.target));
  }
  return true;
}
export function serializeGraph(nodes, edges, viewport, selectionMode) {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: { x: n.position.x, y: n.position.y },
      data: structuredClone(n.data),
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle ?? null,
      targetHandle: e.targetHandle ?? null,
    })),
    viewport: { ...viewport },
    selectionMode,
  };
}
