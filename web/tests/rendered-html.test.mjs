import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html", host: "localhost:3000" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the complete audited replay", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html[^>]*lang="zh-CN"/i);
  assert.match(html, /<title>Auditable NL2SQL · 验证弧线与证据链<\/title>/i);
  assert.match(html, /把一句业务问题/);
  assert.match(html, /变成一条可回查的答案链/);
  assert.match(html, /container-demo-run/);
  assert.match(html, /2026年第一季度非取消订单销售额是多少/);
  assert.match(html, /5,946\.0/);
  assert.match(html, /df7e6219cddf5152d66ad43d490955d928840b883f3db7ad48832d94c5f53499/);
  assert.match(html, /审批门检查/);
  assert.match(html, /本次无需人工介入/);
  assert.match(html, /不代表真实企业数据或生产可靠性/);
  assert.match(html, /https:\/\/47\.84\.34\.86\/nl2sql\/api\/v1\/health/);
  assert.match(html, /https:\/\/47\.84\.34\.86\/nl2sql\/api\/v1\/runs\/container-demo-run/);
  assert.match(html, /http:\/\/localhost:3000\/og\.png/);
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/);
  assert.doesNotMatch(html, /<form\b|<input\b/);
});

test("renders the validation arc with evidence and honest generalization boundaries", async () => {
  const response = await render();
  const html = await response.text();

  const scores = ["14/20", "17/20", "20/20", "30/30", "40/40"];
  let cursor = -1;
  for (const score of scores) {
    const next = html.indexOf(score, cursor + 1);
    assert.ok(next > cursor, `${score} should appear in validation order`);
    cursor = next;
  }

  const evidencePaths = [
    ["model-eval-runner.md", "9"],
    ["training-pair-frozen-eval.md", "19"],
    ["intent-routing-fix.md", "20"],
    ["unseen-success-fix.md", "23"],
    ["hardcase-fix.md", "25"],
    ["schema-summary-injection.md", "30"],
    ["paraphrase-synonym-coverage.md", "29"],
  ];
  for (const [report, pr] of evidencePaths) {
    assert.match(
      html,
      new RegExp(`https://github\\.com/suuny-ab/auditable-nl2sql-agent/blob/main/docs/work/${report}`),
    );
    assert.match(
      html,
      new RegExp(`https://github\\.com/suuny-ab/auditable-nl2sql-agent/pull/${pr}`),
    );
  }

  assert.match(html, /同一 20 题开发集/);
  assert.match(html, /已见开发集满分 ≠ 未见泛化/);
  assert.match(html, /成功题仍为 0\/7/);
  assert.match(html, /投影 27\/30/);
  assert.match(html, /仅复跑 3 条/);
  assert.match(html, /候选假设 · 未实现/);
});

test("removes starter artifacts and keeps local scripts cross-platform", async () => {
  const [page, layout, packageJson, replay] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../app/data/container-demo-run.json", import.meta.url), "utf8"),
  ]);

  assert.doesNotMatch(page, /_sites-preview|codex-preview/);
  assert.doesNotMatch(layout, /Starter Project|codex-preview/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton|drizzle|WRANGLER_LOG_PATH=/);
  assert.match(packageJson, /"name": "auditable-nl2sql-showcase"/);
  assert.match(packageJson, /"dev": "vinext dev"/);
  assert.match(replay, /"schema_version": "showcase-replay-v1"/);
  await assert.rejects(access(new URL("../app/_sites-preview", import.meta.url)));
});
