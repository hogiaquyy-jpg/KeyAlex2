// Netlify Function proxy: trinh duyet goi cung origin -> het loi CORS.
// Chuyen tiep moi request sang API key server that.
const BASE = "https://keyalex2.onrender.com/api/v1";

exports.handler = async function (event) {
  const prefix = "/.netlify/functions/api";
  let path = event.path.indexOf(prefix) === 0 ? event.path.slice(prefix.length) : event.path;
  if (path.charAt(0) !== "/") path = "/" + path;
  const url = BASE + path + (event.rawQuery ? "?" + event.rawQuery : "");

  const headers = { "Content-Type": "application/json" };
  const h = event.headers || {};
  Object.keys(h).forEach(function (k) {
    const lk = k.toLowerCase();
    if (lk === "authorization") headers["Authorization"] = h[k];
    if (lk === "x-admin-key") headers["X-Admin-Key"] = h[k];
  });

  const init = { method: event.httpMethod, headers: headers };
  if (event.body && event.httpMethod !== "GET" && event.httpMethod !== "HEAD") {
    init.body = event.isBase64Encoded ? Buffer.from(event.body, "base64").toString() : event.body;
  }

  try {
    const r = await fetch(url, init);
    const text = await r.text();
    return {
      statusCode: r.statusCode,
      headers: { "Content-Type": r.headers.get("content-type") || "application/json" },
      body: text
    };
  } catch (e) {
    return {
      statusCode: 502,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ success: false, message: "Proxy loi: " + e.message })
    };
  }
};
