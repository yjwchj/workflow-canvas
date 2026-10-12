export async function api(path, options = {}) {
  const { body, ...rest } = options;
  const isForm = body instanceof FormData;
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...rest,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...rest.headers,
    },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });
  let data;
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => `${item.loc.at(-1)}：${item.msg}`).join("；")
      : detail;
    const error = new Error(
      message || `请求失败（${response.status}），请检查后端服务`,
    );
    error.status = response.status;
    throw error;
  }
  return data;
}
