import {
  ref,
  shallowRef,
  computed,
  watch,
  onMounted,
  onUnmounted,
  toRaw,
} from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { canConnect, serializeGraph, imageSelection } from "../lib/graph";

export const canvasContext = Symbol("canvas");
export function useCanvas() {
  const canvases = ref([]),
    templates = ref([]),
    nodes = ref([]),
    edges = ref([]),
    assets = ref([]),
    runs = ref([]);
  const current = ref(null),
    health = ref(null),
    viewport = ref({ x: 0, y: 0, zoom: 1 });
  const mode = shallowRef("manual"),
    saveState = shallowRef("已保存"),
    selectedNodeId = shallowRef(null);
  const loading = shallowRef(true),
    locked = shallowRef(false);
  let saveTimer,
    pollTimer,
    mutation = 0,
    savedMutation = 0,
    pendingSave = Promise.resolve(),
    applying = false;
  const selectedNode = computed(() =>
    nodes.value.find((n) => n.id === selectedNodeId.value),
  );
  const activeRuns = computed(() =>
    runs.value.filter((r) =>
      ["queued", "running", "waiting_selection"].includes(r.status),
    ),
  );
  const assetsByNode = computed(() => {
    const grouped = {};
    for (const asset of assets.value)
      (grouped[asset.node_id] ||= []).push(asset);
    return grouped;
  });
  function graph() {
    return serializeGraph(
      JSON.parse(JSON.stringify(nodes.value)),
      edges.value,
      toRaw(viewport.value),
      mode.value,
    );
  }
  function changed() {
    if (applying || !current.value || locked.value) return;
    mutation++;
    saveState.value = "未保存";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => save().catch(() => {}), 900);
  }
  // Only persistent fields mark the canvas dirty; Flow dimensions/selection do not.
  watch(
    () =>
      JSON.stringify({
        nodes: nodes.value.map((n) => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data,
        })),
        edges: edges.value.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle,
          targetHandle: e.targetHandle,
        })),
        viewport: viewport.value,
        mode: mode.value,
      }),
    changed,
    { flush: "sync" },
  );
  async function save() {
    clearTimeout(saveTimer);
    const operation = pendingSave
      .catch(() => {})
      .then(async () => {
        if (!current.value || mutation === savedMutation) return;
        if (locked.value)
          throw new Error("画布保存冲突，请先导出当前内容并重新加载");
        const id = current.value.id,
          seq = mutation;
        saveState.value = "保存中…";
        try {
          const result = await api(`/canvases/${id}`, {
            method: "PUT",
            body: {
              name: current.value.name,
              graph: graph(),
              revision: current.value.revision,
            },
          });
          if (current.value?.id === id) {
            current.value.revision = result.revision;
            savedMutation = seq;
            saveState.value = mutation === seq ? "已保存" : "未保存";
            const entry = canvases.value.find((c) => c.id === id);
            if (entry) entry.name = result.name;
            if (mutation !== seq) {
              clearTimeout(saveTimer);
              saveTimer = setTimeout(() => save().catch(() => {}), 900);
            }
          }
        } catch (error) {
          saveState.value =
            error.status === 409
              ? "保存冲突 · 请导出后重新加载"
              : "保存失败 · 点击重试";
          if (error.status === 409) locked.value = true;
          ElMessage.error(error.message);
          throw error;
        }
      });
    pendingSave = operation;
    return operation;
  }
  async function refresh() {
    const id = current.value?.id;
    if (!id) return;
    const [newAssets, newRuns, status] = await Promise.all([
      api(`/canvases/${id}/assets`),
      api(`/canvases/${id}/runs`),
      api("/health"),
    ]);
    if (current.value?.id !== id) return;
    assets.value = newAssets;
    runs.value = newRuns;
    health.value = status;
    syncImageChoices();
  }
  function syncImageChoices(savedAt) {
    let updated = false;
    for (const node of nodes.value) {
      if (!["result", "image"].includes(node.type)) continue;
      const next = imageSelection(
        node.data,
        assetsByNode.value[node.id] || [],
        savedAt,
      );
      if (
        next.selectedAssetId !== node.data.selectedAssetId ||
        next.latestSeenAssetId !== node.data.latestSeenAssetId
      ) {
        node.data = next;
        updated = true;
      }
    }
    return updated;
  }
  async function open(id) {
    await save();
    loading.value = true;
    try {
      const [canvas, newAssets, newRuns] = await Promise.all([
        api(`/canvases/${id}`),
        api(`/canvases/${id}/assets`),
        api(`/canvases/${id}/runs`),
      ]);
      applying = true;
      current.value = canvas;
      nodes.value = canvas.graph.nodes.map((n) => ({
        ...n,
        dragHandle: ".node-header",
      }));
      edges.value = canvas.graph.edges;
      viewport.value = canvas.graph.viewport;
      mode.value = canvas.graph.selectionMode;
      assets.value = newAssets;
      runs.value = newRuns;
      selectedNodeId.value = null;
      mutation = 0;
      savedMutation = 0;
      locked.value = false;
      saveState.value = "已保存";
      const choicesUpdated = syncImageChoices(canvas.updated_at);
      applying = false;
      if (choicesUpdated) changed();
      await refresh();
    } finally {
      applying = false;
      loading.value = false;
    }
  }
  async function create(name = "新的创作") {
    await save();
    const canvas = await api("/canvases", { method: "POST", body: { name } });
    canvases.value.unshift(canvas);
    await open(canvas.id);
  }
  function updateNode(id, patch) {
    const node = nodes.value.find((n) => n.id === id);
    if (node) {
      if ("selectedAssetId" in patch)
        patch = {
          ...patch,
          latestSeenAssetId: assetsByNode.value[id]?.at(-1)?.id,
        };
      node.data = { ...node.data, ...patch };
    }
  }
  function addText(position) {
    const id = crypto.randomUUID();
    nodes.value.push({
      id,
      type: "text",
      position: position || newPosition(),
      data: { label: "文字灵感", text: "" },
      dragHandle: ".node-header",
    });
    selectedNodeId.value = id;
  }
  function newPosition() {
    if (nodes.value.length)
      return {
        x: Math.max(...nodes.value.map((n) => n.position.x)) + 350,
        y: nodes.value.at(-1).position.y,
      };
    return {
      x: (160 - viewport.value.x) / viewport.value.zoom,
      y: (140 - viewport.value.y) / viewport.value.zoom,
    };
  }
  function addWorkflow(template) {
    const id = crypto.randomUUID(),
      resultId = crypto.randomUUID(),
      position = newPosition();
    const params = { count: 1 };
    template.parameters.forEach((p) => {
      params[p.key] = p.default;
    });
    nodes.value.push(
      {
        id,
        type: "workflow",
        position,
        dragHandle: ".node-header",
        data: { templateId: template.id, label: template.name, params },
      },
      {
        id: resultId,
        type: "result",
        position: { x: position.x + 370, y: position.y },
        dragHandle: ".node-header",
        data: { label: "图片结果", selectedAssetId: null },
      },
    );
    edges.value.push({
      id: `${id}-${resultId}`,
      source: id,
      target: resultId,
      sourceHandle: "image",
      targetHandle: "image",
    });
    selectedNodeId.value = id;
  }
  function connect(connection) {
    if (!canConnect(connection, nodes.value, edges.value)) {
      ElMessage.warning("连线类型不匹配、输入已连接或存在循环");
      return;
    }
    edges.value.push({ ...connection, id: crypto.randomUUID() });
  }
  function removeSelected() {
    const ids = new Set(
      nodes.value
        .filter((n) => n.selected || n.id === selectedNodeId.value)
        .map((n) => n.id),
    );
    if (
      activeRuns.value.some((r) =>
        r.protected_node_ids?.some((id) => ids.has(id)),
      )
    ) {
      ElMessage.warning("这些节点有未完成任务，请等待任务结束或先取消任务");
      return;
    }
    nodes.value = nodes.value.filter((n) => !ids.has(n.id));
    edges.value = edges.value.filter(
      (e) => !ids.has(e.source) && !ids.has(e.target) && !e.selected,
    );
    selectedNodeId.value = null;
  }
  async function upload(files, position) {
    for (const file of files) {
      if (
        !["image/png", "image/jpeg", "image/webp"].includes(file.type) ||
        file.size > 20 * 1024 * 1024
      ) {
        ElMessage.warning("仅支持不超过 20 MB 的 PNG、JPEG、WebP");
        continue;
      }
      const id = crypto.randomUUID();
      nodes.value.push({
        id,
        type: "image",
        position: position || newPosition(),
        dragHandle: ".node-header",
        data: { label: file.name, selectedAssetId: null },
      });
      try {
        await save();
        const form = new FormData();
        form.append("file", file);
        form.append("node_id", id);
        const asset = await api(`/canvases/${current.value.id}/assets`, {
          method: "POST",
          body: form,
        });
        assets.value.push(asset);
        updateNode(id, { selectedAssetId: asset.id });
        selectedNodeId.value = id;
        await save();
      } catch (error) {
        ElMessage.error(error.message);
      }
    }
  }
  async function run(nodeId = null) {
    await save();
    await api(`/canvases/${current.value.id}/runs`, {
      method: "POST",
      body: { node_id: nodeId },
    });
    await refresh();
    ElMessage.success("任务已提交，参数已固定");
  }
  async function resume(runId) {
    const run = runs.value.find((r) => r.id === runId);
    const node = nodes.value.find((n) => n.id === run.waiting_result_id);
    if (!node?.data.selectedAssetId) {
      ElMessage.warning("请在等待结果节点中选择一张图片");
      return;
    }
    await save();
    await api(`/runs/${runId}/resume`, {
      method: "POST",
      body: { asset_id: node.data.selectedAssetId },
    });
    await refresh();
  }
  async function cancel(runId) {
    await api(`/runs/${runId}/cancel`, { method: "POST" });
    await refresh();
  }
  function exportGraph() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(graph(), null, 2)], {
        type: "application/json",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `${current.value.name}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }
  async function loadTemplates() {
    templates.value = await api("/templates");
  }
  function beforeUnload(event) {
    if (mutation !== savedMutation) {
      event.preventDefault();
      event.returnValue = "";
    }
  }
  onMounted(async () => {
    window.addEventListener("beforeunload", beforeUnload);
    try {
      [canvases.value, templates.value, health.value] = await Promise.all([
        api("/canvases"),
        api("/templates"),
        api("/health"),
      ]);
      if (canvases.value.length) await open(canvases.value[0].id);
      else await create("我的第一张画布");
    } catch (error) {
      ElMessage.error(error.message);
    } finally {
      loading.value = false;
    }
    pollTimer = setInterval(
      () =>
        refresh().catch(() => {
          health.value = null;
        }),
      3000,
    );
  });
  onUnmounted(() => {
    clearTimeout(saveTimer);
    clearInterval(pollTimer);
    window.removeEventListener("beforeunload", beforeUnload);
  });
  return {
    canvases,
    templates,
    nodes,
    edges,
    assets,
    runs,
    current,
    health,
    viewport,
    mode,
    saveState,
    loading,
    selectedNodeId,
    selectedNode,
    activeRuns,
    assetsByNode,
    open,
    create,
    save,
    changed,
    refresh,
    updateNode,
    addText,
    addWorkflow,
    connect,
    removeSelected,
    upload,
    run,
    resume,
    cancel,
    exportGraph,
    loadTemplates,
  };
}
