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

      <section className="replay-section" id="replay">
        <div className="section-heading">
          <p className="section-number">01 / REAL REPLAY</p>
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
          <p className="section-number">02 / EVIDENCE</p>
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
          <p className="section-number">03 / BOUNDARIES</p>
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
        <span>本地静态展示 · 未部署页面 · 2026</span>
      </footer>
    </main>
  );
}
