import replayData from "./data/container-demo-run.json";

type ReplayStep = {
  sequence: number;
  node: string;
  status: string;
  details: Record<string, unknown>;
};

const replay = replayData.record;
const source = replayData.source;
const steps = replay.trajectory as ReplayStep[];
const repoBase = "https://github.com/suuny-ab/auditable-nl2sql-agent";

const stepCopy: Record<string, { label: string; eyebrow: string }> = {
  load_schema: { label: "读取 Schema", eyebrow: "检索" },
  draft_sql: { label: "生成 SQL", eyebrow: "生成" },
  assess_sql: { label: "审批门检查", eyebrow: "人工节点" },
  execute_sql: { label: "只读执行", eyebrow: "执行" },
  validate_result: { label: "校验结果", eyebrow: "校验" },
  bind_evidence: { label: "绑定证据", eyebrow: "证据" },
  compose_answer: { label: "组成回答", eyebrow: "答案" },
  finish: { label: "持久化终态", eyebrow: "完成" },
};

function stepDetail(step: ReplayStep) {
  switch (step.node) {
    case "load_schema":
      return `读取 ${step.details.table_count} 张合成业务表`;
    case "draft_sql":
      return "生成一条聚合查询，未执行写操作";
    case "assess_sql":
      return step.details.approval_required
        ? "触发人工审批，执行暂停"
        : "风险门通过，本次无需人工介入";
    case "execute_sql":
      return `返回 ${step.details.returned_row_count} 行，未截断`;
    case "validate_result":
      return "列、行宽、截断与 JSON 标量全部通过";
    case "bind_evidence":
      return "问题、SQL、结果与 Schema 绑定为 evidence-v1";
    case "compose_answer":
      return "回答只引用证据中的一个结果单元格";
    case "finish":
      return "完整 run record 可按 ID 回查";
    default:
      return "步骤已完成";
  }
}

const evidenceLinks = [
  {
    label: "源码仓库",
    detail: "实现、测试与切片合同",
    href: "https://github.com/suuny-ab/auditable-nl2sql-agent",
  },
  {
    label: "公开 Health",
    detail: "ok · read_only=true",
    href: source.public_health_url,
  },
  {
    label: "Run 原记录",
    detail: source.run_id,
    href: source.public_read_url,
  },
  {
    label: "冻结评测证据",
    detail: "同一 20 条合成集的单次结果",
    href: "https://github.com/suuny-ab/auditable-nl2sql-agent/blob/main/docs/work/model-eval-runner.md",
  },
];

const tuningArc = [
  {
    step: "01",
    score: "14/20",
    label: "冻结基线",
    detail: "同一 20 题开发集 · 首次受控真实调用",
    report: "model-eval-runner.md",
    pr: "9",
  },
  {
    step: "02",
    score: "17/20",
    label: "训练对注入",
    detail: "同一 20 题开发集 · 只复用版本化训练对",
    report: "training-pair-frozen-eval.md",
    pr: "19",
  },
  {
    step: "03",
    score: "20/20",
    label: "意图路由修复",
    detail: "同一 20 题开发集 · 观察错误后定向修复",
    report: "intent-routing-fix.md",
    pr: "20",
  },
  {
    step: "04",
    score: "30/30",
    label: "成功题补齐",
    detail: "主库已见开发集 · 观察失败样本后修复",
    report: "unseen-success-fix.md",
    pr: "23",
  },
  {
    step: "05",
    score: "40/40",
    label: "难例补齐",
    detail: "主库已见 40 题开发集 · 观察错误后修复",
    report: "hardcase-fix.md",
    pr: "25",
  },
];

const generalizationDimensions = [
  {
    score: "40/40",
    label: "主库已见开发集",
    detail: "观察 40 题错误并完成定向修复后的开发集成绩。",
    boundary: "已见开发集满分 ≠ 未见泛化",
    report: "hardcase-fix.md",
    pr: "25",
  },
  {
    score: "最新 9/15",
    label: "换 schema",
    detail:
      "结构摘要历史轮次 8/15；原生注释使 8/15 → 9/15；有限字段值采集保持 9/15。",
    boundary: "成功题 0/7 → 1/7；同一换库集合复测",
    evidence: [
      { label: "结构摘要", report: "schema-summary-injection.md", pr: "30" },
      { label: "原生注释", report: "native-metadata.md", pr: "34" },
      {
        label: "有限字段值",
        report: "low-cardinality-value-collection.md",
        pr: "35",
      },
    ],
  },
  {
    score: "投影 27/30",
    label: "同义改述",
    detail: "旧完整基线 24/30，加上掉分三题的定向结果。",
    boundary: "仅复跑 3 条，不是完整 30 题新轮次",
    evidence: [
      { report: "paraphrase-synonym-coverage.md", pr: "29" },
    ],
  },
];

function EvidencePair({
  report,
  pr,
  label,
}: {
  report: string;
  pr: string;
  label?: string;
}) {
  return (
    <span className="metric-links">
      {label ? <small>{label}</small> : null}
      <a
        href={`${repoBase}/blob/main/docs/work/${report}`}
        target="_blank"
        rel="noreferrer"
      >
        报告 ↗
      </a>
      <a href={`${repoBase}/pull/${pr}`} target="_blank" rel="noreferrer">
        PR #{pr} ↗
      </a>
    </span>
  );
}

function EvidenceList({
  evidence,
}: {
  evidence: Array<{ report: string; pr: string; label?: string }>;
}) {
  return (
    <div className="evidence-list">
      {evidence.map((item) => (
        <EvidencePair
          key={`${item.report}-${item.pr}`}
          report={item.report}
          pr={item.pr}
          label={item.label}
        />
      ))}
    </div>
  );
}

export default function Home() {
  return (
    <main>
      <a className="skip-link" href="#replay">
        跳到真实回放
      </a>

      <header className="site-header">
        <a className="brand" href="#top" aria-label="Auditable NL2SQL 首页">
          <span className="brand-mark">NL→SQL</span>
          <span className="brand-name">Auditable Agent</span>
        </a>
        <nav aria-label="主要导航">
          <a href="#validation">验证弧线</a>
          <a href="#replay">真实回放</a>
          <a href="#proof">证据入口</a>
          <a href="#boundaries">能力边界</a>
        </nav>
        <span className="health-chip">
          <span className="health-dot" aria-hidden="true" />
          Read-only API
        </span>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="kicker">可审计 NL2SQL · 合成数据作品集</p>
          <h1>
            把一句业务问题，
            <span>变成一条可回查的答案链。</span>
          </h1>
          <p className="hero-lede">
            不只展示答案。这里把 SQL、只读执行、审批判断、结果校验、证据指纹与最终回答放回同一个
            run，让每一步都有出处。
          </p>
          <div className="hero-actions">
            <a className="button button-primary" href="#replay">
              查看真实回放 <span aria-hidden="true">↓</span>
            </a>
            <a
              className="button button-secondary"
              href="https://github.com/suuny-ab/auditable-nl2sql-agent"
              target="_blank"
              rel="noreferrer"
            >
              查看源码 <span aria-hidden="true">↗</span>
            </a>
          </div>
          <ul className="boundary-pills" aria-label="核心边界">
            <li>只用合成数据</li>
            <li>数据库机械只读</li>
            <li>页面只做静态回放</li>
          </ul>
        </div>

        <div className="hero-console" aria-label="Run 回放摘要">
          <div className="console-topbar">
            <span className="console-title">run / {replay.run_id}</span>
            <span className="console-status">completed</span>
          </div>
          <div className="console-question">
            <span className="console-prompt">Q</span>
            <p>{replay.question}</p>
          </div>
          <div className="console-flow" aria-label="答案链摘要">
            <div>
              <span>01</span>
              <p>SQL</p>
              <strong>SELECT SUM(…)</strong>
            </div>
            <div>
              <span>02</span>
              <p>RESULT</p>
              <strong>¥ 5,946.00</strong>
            </div>
            <div>
              <span>03</span>
              <p>EVIDENCE</p>
              <strong>df7e6219…3499</strong>
            </div>
          </div>
          <div className="console-answer">
            <span>ANSWER</span>
            <p>{replay.answer.text}</p>
          </div>
          <p className="console-footnote">来自公开只读 run record · 非现场模型调用</p>
        </div>
      </section>

      <section className="signal-strip" aria-label="回放事实摘要">
        <div>
          <strong>8</strong>
          <span>trajectory 节点</span>
        </div>
        <div>
          <strong>1</strong>
          <span>SQL 执行次数</span>
        </div>
        <div>
          <strong>4</strong>
          <span>合成业务表</span>
        </div>
        <div>
          <strong>0</strong>
          <span>页面写入入口</span>
        </div>
      </section>

      <section className="validation-section" id="validation">
        <div className="section-heading validation-heading">
          <p className="section-number">01 / VALIDATION ARC</p>
          <h2>成绩会涨，证据边界不能跟着膨胀。</h2>
          <p>
            五次成绩来自受控开发过程。每一步都回指版本化报告与代码变更，但这条线记录的是调优轨迹，
            不是五次独立未见评测。
          </p>
        </div>

        <div className="validation-warning" role="note">
          <strong>读图边界</strong>
          <span>前三步复用同一 20 题开发集；后两步也是观察错误后修复的主库开发集。</span>
          <b>已见开发集满分 ≠ 未见泛化</b>
        </div>

        <ol className="validation-arc" aria-label="五步调优成绩弧线">
          {tuningArc.map((milestone) => (
            <li key={milestone.step}>
              <article className="arc-card">
                <span className="arc-step">{milestone.step}</span>
                <strong className="arc-score">{milestone.score}</strong>
                <h3>{milestone.label}</h3>
                <p>{milestone.detail}</p>
                <EvidencePair report={milestone.report} pr={milestone.pr} />
              </article>
            </li>
          ))}
        </ol>

        <div className="generalization-heading">
          <p className="section-number">THREE DIMENSIONS</p>
          <h3>把主库成绩、换库能力和语言改述拆开看。</h3>
        </div>
        <div className="generalization-grid">
          {generalizationDimensions.map((dimension) => (
            <article className="dimension-card" key={dimension.label}>
              <p>{dimension.label}</p>
              <strong>{dimension.score}</strong>
              <span>{dimension.detail}</span>
              <b>{dimension.boundary}</b>
              <EvidenceList
                evidence={
                  "evidence" in dimension
                    ? dimension.evidence
                    : [{ report: dimension.report, pr: dimension.pr }]
                }
              />
            </article>
          ))}
        </div>

        <div className="shortfall-panel">
          <div className="shortfall-finding">
            <p className="section-number">EXPOSED SHORTFALL</p>
            <strong>1/7</strong>
            <h3>元数据和值可见 ≠ 业务合同完整</h3>
            <p>
              原生注释让成功题从 0/7 → 1/7；有限字段值采集未新增提升。剩余成功题 6/7 的已知缺口
              集中在金额单位、输出列 / 行合同与有界查询 / 审批合同。
            </p>
            <EvidenceList
              evidence={[
                { label: "结构摘要", report: "schema-summary-injection.md", pr: "30" },
                { label: "原生注释", report: "native-metadata.md", pr: "34" },
                {
                  label: "有限字段值",
                  report: "low-cardinality-value-collection.md",
                  pr: "35",
                },
              ]}
            />
          </div>
          <div className="route-list">
            <p className="route-label">已实现改道 · 结果分层</p>
            <ol>
              <li>SQLite 原生注释已接入：总正确 8/15 → 9/15，成功题 0/7 → 1/7。</li>
              <li>5 个低基数字段的 17 个值已接入：9/15、1/7 持平，没有新增提升。</li>
              <li>剩余 6/7 需要新的产品切片处理业务合同，本次事实同步不继续调优。</li>
            </ol>
            <small>三轮来自同一换库集合的开发复测，不是新的 unseen 证据或生产可靠性证明。</small>
          </div>
        </div>
      </section>

      <section className="replay-section" id="replay">
        <div className="section-heading">
          <p className="section-number">02 / REAL REPLAY</p>
          <h2>不是示意图，是一个真实完成的 run。</h2>
          <p>
            页面快照来自公开只读接口，并由同一产品 fixture 重新生成后逐字段校验。run ID 可直接回查。
          </p>
        </div>

        <div className="replay-grid">
          <article className="question-card">
            <div className="card-label">
              <span>自然语言问题</span>
              <span className="verified-badge">verified</span>
            </div>
            <blockquote>“{replay.question}”</blockquote>
            <dl className="run-meta">
              <div>
                <dt>run_id</dt>
                <dd>{replay.run_id}</dd>
              </div>
              <div>
                <dt>status</dt>
                <dd>{replay.status}</dd>
              </div>
              <div>
                <dt>data</dt>
                <dd>synthetic ecommerce</dd>
              </div>
            </dl>
          </article>

          <article className="result-card">
            <span className="card-label">查询结果</span>
            <div className="result-value">
              <span>revenue</span>
              <strong>5,946.0</strong>
            </div>
            <p>{replay.answer.text}</p>
            <div className="validation-row">
              <span>result-validation</span>
              <strong>5 / 5 passed</strong>
            </div>
          </article>
        </div>

        <details className="sql-panel" open>
          <summary>
            <span>生成并实际执行的 SQL</span>
            <span className="sql-safety">READ ONLY</span>
          </summary>
          <pre>
            <code>{replay.generated_sql}</code>
          </pre>
        </details>

        <div className="trajectory" aria-label="完整 trajectory">
          {steps.map((step) => {
            const copy = stepCopy[step.node] ?? {
              label: step.node,
              eyebrow: "STEP",
            };
            return (
              <article className="trajectory-step" key={step.sequence}>
                <div className="step-index">{String(step.sequence).padStart(2, "0")}</div>
                <div className="step-line" aria-hidden="true" />
                <div className="step-copy">
                  <p>{copy.eyebrow}</p>
                  <h3>{copy.label}</h3>
                  <span>{stepDetail(step)}</span>
                </div>
                <span className="step-status">{step.status}</span>
              </article>
            );
          })}
        </div>
      </section>

      <section className="evidence-section" id="proof">
        <div className="evidence-copy">
          <p className="section-number">03 / EVIDENCE</p>
          <h2>答案不是终点，证据链才是。</h2>
          <p>
            这个回答只引用结果中的一个单元格。问题、SQL、Schema 快照、查询结果与校验回执共同形成
            <code> evidence-v1</code>，指纹可在独立进程重算。
          </p>
          <div className="fingerprint-card">
            <span>SHA-256 · canonical-json-v1</span>
            <code>{replay.evidence.fingerprint.value}</code>
          </div>
        </div>

        <div className="evidence-links">
          {evidenceLinks.map((link) => (
            <a key={link.label} href={link.href} target="_blank" rel="noreferrer">
              <span>
                <strong>{link.label}</strong>
                <small>{link.detail}</small>
              </span>
              <span aria-hidden="true">↗</span>
            </a>
          ))}
        </div>
      </section>

      <section className="boundaries-section" id="boundaries">
        <div className="section-heading compact">
          <p className="section-number">04 / BOUNDARIES</p>
          <h2>把能证明的，与不能证明的分开。</h2>
        </div>
        <div className="boundary-grid">
          <article className="boundary-card can-prove">
            <span className="boundary-icon" aria-hidden="true">✓</span>
            <h3>这页能证明</h3>
            <ul>
              <li>固定合成 run 的 8 步轨迹可回查</li>
              <li>执行结果与证据指纹、回答绑定</li>
              <li>数据库连接与授权边界机械只读</li>
              <li>公开 API 仅提供 health 与 run 查询</li>
            </ul>
          </article>
          <article className="boundary-card cannot-prove">
            <span className="boundary-icon" aria-hidden="true">×</span>
            <h3>这页不能证明</h3>
            <ul>
              <li>不代表真实企业数据或生产可靠性</li>
              <li>不提供现场提问或自动创建 run</li>
              <li>同一冻结评测集不代表泛化提升</li>
              <li>SHA-256 不是数字签名或语义正确保证</li>
            </ul>
          </article>
        </div>
      </section>

      <section className="closing-section">
        <p>READ-ONLY · TRACEABLE · SYNTHETIC</p>
        <h2>先看证据，再相信答案。</h2>
        <a href="#replay">从问题开始重放 <span aria-hidden="true">↑</span></a>
      </section>

      <footer>
        <span>Auditable NL2SQL Agent</span>
        <span>v2 公开事实已同步 · 尚未部署 · 2026</span>
      </footer>
    </main>
  );
}
