// Builds the IEEE-format paper (two-column conference layout) as a .docx
// Run:  node build_paper.js   ->  IEEE_Paper_Prompt_Injection_Runtime_Guard.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, BorderStyle,
  AlignmentType, HeadingLevel, SectionType, LevelFormat, TabStopType, VerticalAlign,
  Math: OMath, MathRun, MathFraction, MathSubScript, MathSuperScript, MathRoundBrackets, MathSum, MathFunction, MathLimitLower,
} = require("docx");

const FONT = "Times New Roman";
const COL = 5040;          // one IEEE column (3.5 in) in DXA
const FIG = path.join(__dirname, "figures");
const OUT = path.join(__dirname, "IEEE_Paper_Prompt_Injection_Runtime_Guard.docx");

// ------------------------------------------------------------------ references (IEEE style)
const REFS = {
  react: 'S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, "ReAct: Synergizing reasoning and acting in language models," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2023.',
  toolformer: 'T. Schick, J. Dwivedi-Yu, R. Dessì, R. Raileanu, M. Lomeli, L. Zettlemoyer, N. Cancedda, and T. Scialom, "Toolformer: Language models can teach themselves to use tools," in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2023.',
  greshake: 'K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, "Not what you\'ve signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection," in *Proc. 16th ACM Workshop Artif. Intell. Secur. (AISec)*, 2023.',
  owasp: 'OWASP Foundation, "OWASP Top 10 for large language model applications 2025: LLM01 prompt injection," 2025. [Online]. Available: https://genai.owasp.org/llmrisk/llm01-prompt-injection/',
  injecagent: 'Q. Zhan, Z. Liang, Z. Ying, and D. Kang, "InjecAgent: Benchmarking indirect prompt injections in tool-integrated large language model agents," in *Findings Assoc. Comput. Linguistics (ACL)*, 2024.',
  agentdojo: 'E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, and F. Tramèr, "AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents," in *Adv. Neural Inf. Process. Syst. (NeurIPS) Datasets and Benchmarks Track*, 2024.',
  protectai: 'Protect AI, "Fine-tuned DeBERTa-v3-base for prompt injection detection (v2)," model card (Kaggle mirror), 2024. [Online]. Available: https://www.kaggle.com/models/aisuko/deberta-v3-base-prompt-injection-v2',
  promptguard: 'Meta, "Llama Prompt Guard (86M) model card," 2024. [Online]. Available: https://www.kaggle.com/models/metaresearch/llama-3.1-prompt-guard',
  denning: 'D. E. Denning, "An intrusion-detection model," *IEEE Trans. Softw. Eng.*, vol. SE-13, no. 2, pp. 222–232, 1987.',
  forrest: 'S. Forrest, S. A. Hofmeyr, A. Somayaji, and T. A. Longstaff, "A sense of self for Unix processes," in *Proc. IEEE Symp. Security and Privacy*, 1996, pp. 120–128.',
  perez: 'F. Perez and I. Ribeiro, "Ignore previous prompt: Attack techniques for language models," in *NeurIPS ML Safety Workshop*, 2022.',
  liu: 'Y. Liu, Y. Jia, R. Geng, J. Jia, and N. Z. Gong, "Formalizing and benchmarking prompt injection attacks and defenses," in *Proc. 33rd USENIX Security Symp.*, 2024.',
  shen: 'X. Shen, Z. Chen, M. Backes, Y. Shen, and Y. Zhang, "‘Do Anything Now’: Characterizing and evaluating in-the-wild jailbreak prompts on large language models," in *Proc. ACM SIGSAC Conf. Comput. Commun. Secur. (CCS)*, 2024.',
  toolemu: 'Y. Ruan, H. Dong, A. Wang, S. Pitis, Y. Zhou, J. Ba, Y. Dubois, C. J. Maddison, and T. Hashimoto, "Identifying the risks of LM agents with an LM-emulated sandbox," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2024.',
  deberta: 'P. He, J. Gao, and W. Chen, "DeBERTaV3: Improving DeBERTa using ELECTRA-style pre-training with gradient-disentangled embedding sharing," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2023.',
  struq: 'S. Chen, J. Piet, C. Sitawarin, and D. Wagner, "StruQ: Defending against prompt injection with structured queries," in *Proc. 34th USENIX Security Symp.*, 2025.',
  hierarchy: 'E. Wallace, K. Xiao, R. Leike, L. Weng, J. Heidecke, and A. Beutel, "The instruction hierarchy: Training LLMs to prioritize privileged instructions," arXiv:2404.13208, 2024.',
  spotlight: 'K. Hines, G. Lopez, M. Hall, F. Zarfati, Y. Zunger, and E. Kiciman, "Defending against indirect prompt injection attacks with spotlighting," arXiv:2403.14720, 2024.',
  camel: 'E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, and F. Tramèr, "Defeating prompt injections by design," arXiv:2503.18813, 2025.',
  melon: 'K. Zhu, X. Yang, J. Wang, W. Guo, and W. Y. Wang, "MELON: Provable defense against indirect prompt injection attacks in AI agents," in *Proc. Int. Conf. Mach. Learn. (ICML)*, 2025.',
  iforest: 'F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation forest," in *Proc. 8th IEEE Int. Conf. Data Mining (ICDM)*, 2008, pp. 413–422.',
  modernbert: 'B. Warner *et al.*, "Smarter, better, faster, longer: A modern bidirectional encoder for fast, memory efficient, and long context finetuning and inference," arXiv:2412.13663, 2024.',
  wolf: 'Patronus Studio, "Wolf Defender prompt-injection detector (v2)," model card (Kaggle mirror), 2026. [Online]. Available: https://www.kaggle.com/models/aisuko/wolf-defender-prompt-injection',
  minilm: 'W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, "MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers," in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2020.',
  sbert: 'N. Reimers and I. Gurevych, "Sentence-BERT: Sentence embeddings using Siamese BERT-networks," in *Proc. EMNLP-IJCNLP*, 2019.',
  xgboost: 'T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in *Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discov. Data Min.*, 2016, pp. 785–794.',
  stacking: 'D. H. Wolpert, "Stacked generalization," *Neural Netw.*, vol. 5, no. 2, pp. 241–259, 1992.',
  kg_chuneeb: 'chuneeb, "AI Agent Cybersecurity Dataset 2026," Kaggle. Accessed: Oct. 24, 2026. [Online]. Available: https://www.kaggle.com/datasets/chuneeb/ai-agent-cybersecurity-dataset-2026',
  kg_krish: 'krishnayadav456wrsty, "Prompt Injection & Jailbreak Detection Dataset," Kaggle. Accessed: Oct. 24, 2026. [Online]. Available: https://www.kaggle.com/datasets/krishnayadav456wrsty/prompt-injection-and-jailbreak-detection-dataset',
  kg_mpdd: 'mohammedaminejebbar, "Malicious Prompt Detection Dataset (MPDD)," Kaggle. Accessed: Oct. 24, 2026. [Online]. Available: https://www.kaggle.com/datasets/mohammedaminejebbar/malicious-prompt-detection-dataset-mpdd',
  kg_abdul: 'abdul5445, "LLM Prompt Injection Classification Dataset," Kaggle. Accessed: Oct. 24, 2026. [Online]. Available: https://www.kaggle.com/datasets/abdul5445/llm-prompt-injection-classification-dataset',
  sklearn: 'F. Pedregosa *et al.*, "Scikit-learn: Machine learning in Python," *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011.',
};
const order = [];
function citeNums(keys) {
  return keys.map((k) => {
    if (!REFS[k]) throw new Error("unknown ref " + k);
    if (!order.includes(k)) order.push(k);
    return order.indexOf(k) + 1;
  });
}
function citeText(keys) {
  const n = citeNums(keys).sort((a, b) => a - b);
  const parts = [];
  for (let i = 0; i < n.length; ) {
    let j = i;
    while (j + 1 < n.length && n[j + 1] === n[j] + 1) j++;
    parts.push(j - i >= 2 ? `[${n[i]}]–[${n[j]}]` : n.slice(i, j + 1).map((x) => `[${x}]`).join(", "));
    i = j + 1;
  }
  return parts.join(", ");
}

// ------------------------------------------------------------------ inline markup -> runs
// **bold**  *italic*  _{sub}  ^{sup}  `mono`  {@ref1,ref2}  [[placeholder]]
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|_\{[^}]+\}|\^\{[^}]+\}|`[^`]+`|\{@[^}]+\}|\[\[[^\]]+\]\])/g;
  let last = 0, m;
  const add = (t, o = {}) => t && out.push(new TextRun({ text: t, font: FONT, ...base, ...o }));
  while ((m = re.exec(text))) {
    add(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) add(tok.slice(2, -2), { bold: true });
    else if (tok.startsWith("*")) add(tok.slice(1, -1), { italics: true });
    else if (tok.startsWith("_{")) add(tok.slice(2, -1), { subScript: true });
    else if (tok.startsWith("^{")) add(tok.slice(2, -1), { superScript: true });
    else if (tok.startsWith("`")) out.push(new TextRun({ text: tok.slice(1, -1), font: "Courier New", ...base, size: Math.round((base.size || 20) * 0.9) }));
    else if (tok.startsWith("{@")) add(citeText(tok.slice(2, -1).split(",").map((s) => s.trim())));
    else add(tok.slice(2, -2), { highlight: "yellow" });
    last = m.index + tok.length;
  }
  add(text.slice(last));
  return out;
}

// ------------------------------------------------------------------ block helpers
const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
let h1n = 0, h2n = 0, figN = 0, tabN = 0, eqN = 0;

const P = (text, o = {}) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED, indent: { firstLine: o.noIndent ? 0 : 202 },
  spacing: { after: 0, line: 240 }, children: runs(text, { size: 20 }),
});
const H1 = (title) => {
  h2n = 0;
  return new Paragraph({
    heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { before: 200, after: 80 }, keepNext: true,
    children: [new TextRun({ text: `${ROMAN[h1n++]}. ${title}`, font: FONT, size: 20, smallCaps: true, color: "000000" })],
  });
};
const H1u = (title) => new Paragraph({   // unnumbered (Acknowledgment, References)
  heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { before: 200, after: 80 }, keepNext: true,
  children: [new TextRun({ text: title, font: FONT, size: 20, smallCaps: true, color: "000000" })],
});
const H2 = (title) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 100, after: 40 }, keepNext: true,
  children: [new TextRun({ text: `${String.fromCharCode(65 + h2n++)}. ${title}`, font: FONT, size: 20, italics: true, color: "000000" })],
});
const Bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 20, line: 240 }, children: runs(text, { size: 20 }),
});

function Eq(children) {
  eqN++;
  return new Paragraph({
    tabStops: [{ type: TabStopType.CENTER, position: COL / 2 }, { type: TabStopType.RIGHT, position: COL }],
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: "\t", font: FONT }), new OMath({ children }),
      new TextRun({ text: `\t(${eqN})`, font: FONT, size: 20 })],
  });
}
const mr = (t) => new MathRun(t);
const sub = (b, s) => new MathSubScript({ children: [mr(b)], subScript: [mr(s)] });
const fn = (name, children) => new MathFunction({ name: [typeof name === "string" ? mr(name) : name], children });
const curly = (t) => t.replace(/"([^"]*)"/g, "“$1”");

function Figure(file, caption, widthIn = 3.3) {
  figN++;
  const buf = fs.readFileSync(path.join(FIG, file));
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);   // PNG header
  const wpx = Math.round(widthIn * 96);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: Math.round(wpx * h / w) },
        altText: { title: `Fig. ${figN}`, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 140 },
      children: [new TextRun({ text: `Fig. ${figN}. `, font: FONT, size: 16 }), ...runs(caption, { size: 16 })] }),
  ];
}

const rule = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
// rows: arrays of strings or {t, span, bold, align}; header: array of rows (each array of cells)
function Tbl(title, widths, header, rows, note) {
  tabN++;
  const total = widths.reduce((a, b) => a + b, 0);
  const mkCell = (c, ci, isHead, last, colIndex, keep) => {
    const cell = typeof c === "string" ? { t: c } : c;
    const span = cell.span || 1;
    const w = widths.slice(colIndex, colIndex + span).reduce((a, b) => a + b, 0);
    return new TableCell({
      columnSpan: span > 1 ? span : undefined, rowSpan: cell.rowSpan,
      width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      margins: { top: 25, bottom: 25, left: 50, right: 50 },
      borders: { top: none, left: none, right: none, bottom: isHead && last ? rule : none },
      children: [new Paragraph({ alignment: cell.align || (colIndex === 0 ? AlignmentType.LEFT : AlignmentType.CENTER),
        keepNext: keep, children: runs(cell.t, { size: 15, bold: !!cell.bold }) })],
    });
  };
  const build = (cells, isHead, last, keep = true) => {
    let col = 0;
    return new TableRow({ tableHeader: isHead, cantSplit: true, children: cells.map((c, i) => {
      const cell = mkCell(c, i, isHead, last, col, keep);
      col += (typeof c === "string" ? 1 : c.span || 1);
      return cell;
    }) });
  };
  const trs = [
    ...header.map((r, i) => build(r, true, i === header.length - 1)),
    ...rows.map((r, i) => build(r, false, false, i < rows.length - 1)),
  ];
  const out = [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 0 }, keepNext: true,
      children: [new TextRun({ text: `TABLE ${ROMAN[tabN - 1]}`, font: FONT, size: 16, smallCaps: true })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, keepNext: true,
      children: runs(title, { size: 16, smallCaps: true }) }),
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER,
      borders: { top: rule, bottom: rule, left: none, right: none, insideHorizontal: none, insideVertical: none },
      rows: trs }),
  ];
  out.push(new Paragraph({ spacing: { after: 140 }, alignment: AlignmentType.LEFT,
    children: note ? runs(note, { size: 14 }) : [] }));
  return out;
}

// ------------------------------------------------------------------ front matter
const title = new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 240 },
  children: [new TextRun({ text: "Runtime Detection and Prevention of Prompt Injection Attacks in Autonomous LLM Agents Using Behavioural Analysis", font: FONT, size: 48 })],
});
function authorCell(i) {
  const line = (t, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, children: runs(t, { size: 20, ...o }) });
  return new TableCell({
    width: { size: 3480, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none },
    children: [
      line(`[[Author Name ${i}]]`, { size: 22 }),
      line("[[Department of Computer Science and Engineering]]", { italics: true }),
      line("[[Institution Name]]", { italics: true }),
      line("[[City, Country]]"),
      line(`[[author${i}@institution.edu]]`),
    ],
  });
}
const authors = new Table({
  width: { size: 10440, type: WidthType.DXA }, columnWidths: [3480, 3480, 3480],
  borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none },
  rows: [new TableRow({ children: [authorCell(1), authorCell(2), authorCell(3)] })],
});

const abstract = new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 100 },
  children: [
    new TextRun({ text: "Abstract", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ text: "—", font: FONT, size: 18, bold: true }),
    ...runs("Autonomous agents built on large language models (LLMs) read untrusted content such as e-mails, web pages and product reviews through tools and then act on it with the user's privileges. Indirect prompt injection exploits this channel: instructions hidden in tool outputs hijack the agent into transferring money, unlocking doors or exfiltrating private data. Detectors that inspect text alone miss injections phrased as ordinary requests. We present a three-layer runtime guard that wraps every tool call of an agent. Layer 1 scans untrusted tool outputs with a stacked ensemble that combines two benchmark detectors published on Kaggle (ProtectAI DeBERTa-v3 and Wolf Defender) with TF-IDF and MiniLM-based classifiers trained on 69,072 de-duplicated prompts from three Kaggle datasets. Layer 2, the core contribution, is a behavioural monitor that scores each proposed tool call using 18 features describing goal alignment, drift toward untrusted content, argument provenance, tool risk and exfiltration flow. Layer 3 enforces a prevention policy with graded security alerts and session lockdown. The ensemble reaches an F1-score of 0.954 in-distribution and 0.968 on an unseen Kaggle dataset, compared with 0.76–0.80 for the benchmark detectors in-distribution. On 8,432 agent traces derived from the InjecAgent benchmark, including hard negatives in which the user legitimately requests the same sensitive actions, the behavioural monitor detects hijacked tool calls with an F1-score of 0.993 and a 0.28% false-alarm rate on attacker goals unseen during training. The complete guard prevented every hijacked trajectory while 99.1% of benign tasks completed uninterrupted, adding about 25 ms per tool call on a CPU.", { size: 18, bold: true }),
  ],
});
const keywords = new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 },
  children: [
    new TextRun({ text: "Index Terms", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ text: "—prompt injection, large language model agents, behavioural analysis, runtime monitoring, intrusion detection, AI security.", font: FONT, size: 18, bold: true }),
  ],
});

// ------------------------------------------------------------------ body
const body = [abstract, keywords];
const add = (...xs) => xs.flat().forEach((x) => body.push(x));

add(H1("Introduction"));
add(P("Large language models (LLMs) are increasingly deployed as autonomous agents that plan and invoke external tools {@react,toolformer}. An e-mail assistant reads the inbox, a shopping agent reads product reviews and a home assistant controls smart locks. Every such tool output is data from a party the user does not control, yet it enters the same context window as the user's instruction. *Indirect prompt injection* {@greshake} abuses this: an attacker plants an instruction in content the agent will read, and the model, unable to reliably separate data from instructions, executes it with the user's privileges. Prompt injection is ranked first in the OWASP Top 10 for LLM applications {@owasp}, and benchmarks show that capable agents remain vulnerable {@injecagent,agentdojo}."));
add(P("Most deployed defences inspect text. Classifiers such as ProtectAI's DeBERTa-v3 detector {@protectai} and Meta's Prompt Guard {@promptguard} flag injection-like strings. They are effective against overt attacks (“ignore all previous instructions”) but face a fundamental ambiguity: the sentence “please e-mail my saved addresses to amy.watson@gmail.com” is benign when typed by the user and malicious when embedded in a product review. No text-only model can resolve this, because the difference lies in *provenance* and in what the agent *does next*, not in the words."));
add(P("We therefore adopt a behavioural-analysis view inspired by host-based intrusion detection, where processes are monitored through the system calls they make {@denning,forrest}. For an agent, tool calls play the role of system calls. At runtime, before each call executes, we ask: is this action explained by the user's goal, or by untrusted content the agent has just read? Our contributions are:"));
add(Bullet("A three-layer runtime architecture (content detection, behavioural monitoring, and prevention with security alerting) that wraps the tools of any agent without modifying the underlying LLM."));
add(Bullet("A benchmark of two Kaggle-hosted injection detectors against classifiers trained on three Kaggle datasets, and a stacked ensemble that is the most accurate model both in-distribution and on an unseen dataset."));
add(Bullet("An 18-feature behavioural representation of tool calls covering goal alignment, drift, argument provenance (taint), capability risk and exfiltration flow, and a monitor that detects hijacked calls for attacker goals and user tasks unseen during training."));
add(Bullet("An evaluation on 8,432 InjecAgent-derived traces that includes hard negatives in which the user legitimately requests the same sensitive actions, an end-to-end attack-success and utility analysis, and an open implementation with an interactive demonstrator."));
add(P("Section II reviews related work, Section III defines the threat model, Section IV presents the system, Sections V and VI describe the experiments and results, Section VII discusses limitations and Section VIII concludes."));

add(H1("Related Work"));
add(H2("Prompt Injection Attacks"));
add(P("Perez and Ribeiro showed that goal hijacking and prompt leaking can be achieved with simple handcrafted prompts {@perez}. Greshake et al. introduced indirect prompt injection against LLM-integrated applications, where the payload arrives through retrieved data rather than from the user {@greshake}. Liu et al. formalised injection attacks and benchmarked attacks and defences across tasks {@liu}, and Shen et al. characterised thousands of in-the-wild jailbreak prompts {@shen}, a collection that also appears in our training data."));
add(H2("Agent Benchmarks"));
add(P("InjecAgent {@injecagent} pairs 17 user tasks with 62 attacker goals over realistic tool specifications, grouped into direct-harm and data-stealing attacks, each in a base and an “enhanced” phrasing. AgentDojo {@agentdojo} provides a dynamic environment with stateful tasks and adaptive attacks, and ToolEmu {@toolemu} uses an LM-emulated sandbox to surface risky agent behaviour. We build our behavioural traces on InjecAgent."));
add(H2("Defences"));
add(P("Detection defences classify text as benign or injected; public examples include fine-tuned DeBERTa-v3 models {@protectai,deberta} and Prompt Guard {@promptguard}. Prompt- and training-level defences separate data from instructions: StruQ {@struq} trains models on structured queries, the instruction hierarchy {@hierarchy} teaches models to prioritise privileged instructions, and spotlighting {@spotlight} marks untrusted content. System-level designs such as CaMeL {@camel} enforce control- and data-flow separation through a capability-based interpreter, giving strong guarantees at the cost of re-architecting the agent. MELON {@melon} detects attacks behaviourally by re-executing the agent with the user prompt masked and comparing tool calls, which roughly doubles inference cost. Our monitor is complementary: it operates on the observable trace of a single run, requires no change to the agent or model and adds one lightweight classifier evaluation per tool call."));
add(H2("Behavioural Intrusion Detection"));
add(P("Denning's intrusion-detection model {@denning} and the system-call monitoring of Forrest et al. {@forrest} established that deviations from expected behaviour reveal compromise even when the attack payload itself is unknown. Unsupervised anomaly detectors such as Isolation Forest {@iforest} are a common instantiation, which we include as a baseline."));

add(H1("Threat Model and Problem Formulation"));
add(H2("Agent Model"));
add(P("A user issues a goal *g*. At step *t* the agent, given the history *H*_{t} = (*g*, *a*_{1}, *o*_{1}, …, *a*_{t−1}, *o*_{t−1}), proposes a tool call *a*_{t} = (τ_{t}, θ_{t}) consisting of a tool τ_{t} and arguments θ_{t}. Executing it returns an observation *o*_{t}."));
add(H2("Adversary"));
add(P("The attacker controls part of at least one observation (for example a review, an e-mail or a web page) but not *g*, the system prompt, the model weights or the tools. The attacker aims to make the agent execute attacker-chosen calls, either *direct harm* (financial transfer, physical access, deletion) or *data stealing* (reading private data and sending it to an attacker-controlled destination) {@injecagent}."));
add(H2("Defender and Objectives"));
add(P("A runtime monitor sits between the agent and its tools. Before *a*_{t} executes it estimates *P*(*a*_{t} is injection-induced | *g*, *H*_{t}) and may block the call; after execution it may sanitise *o*_{t} before the LLM reads it. The defender has no access to model internals. Let *T*_{h} be the set of hijacked trajectories. Security is measured by the attack success rate"));
add(Eq([fn("ASR", [mr("="), new MathFraction({ numerator: [mr("1")], denominator: [mr("|"), sub("T", "h"), mr("|")] }),
  new MathSum({ children: [mr("s(ω)")], subScript: [mr("ω∈"), sub("T", "h")] })])]));
add(P("where *s*(ω) = 1 if all attacker calls in trajectory ω execute and 0 otherwise. Utility is the fraction of benign trajectories that complete with no legitimate call blocked and no clean content removed.", { noIndent: true }));

add(H1("Proposed System"));
add(H2("Architecture"));
add(P("Fig. 1 shows the guard. It is exposed as a wrapper: each tool function *f* is replaced by `guard.wrap(name, f)`, so every call and every result passes through the guard regardless of the agent framework, and the LLM itself is unchanged."));
add(Figure("fig1_architecture.png", "Architecture of the runtime guard. Layer 1 sanitises untrusted tool outputs *o*_{t}; Layer 2 scores every proposed call *a*_{t} against the user goal *g* before execution; Layer 3 applies the prevention policy and raises security alerts."));
add(H2("Layer 1: Content Detection"));
add(P("Tool outputs are often structured (JSON or dictionaries). We parse them and extract string leaves; unstructured text is split at sentence and paragraph boundaries. Only segments with at least four words are scored, because shorter fields (identifiers, status flags) cannot carry an instruction and caused false alarms in preliminary tests. Each segment *x* is scored by *K* = 4 detectors: (i) ProtectAI DeBERTa-v3-base v2 {@protectai,deberta} and (ii) Wolf Defender, a ModernBERT-architecture encoder {@modernbert,wolf}, both obtained from Kaggle Models; (iii) word (1–2-gram) and character (2–5-gram) TF-IDF features with logistic regression; and (iv) all-MiniLM-L6-v2 sentence embeddings {@minilm,sbert} concatenated with 20 lexical cues (override phrases, role-play markers, fake delimiters, exfiltration verbs and similar) and classified with XGBoost {@xgboost}. For multi-class detectors the injection probability is one minus the probability of the benign labels. Scores are combined by stacked generalisation {@stacking}:"));
add(Eq([mr("ŝ(x)=σ"), new MathRoundBrackets({ children: [sub("w", "0"), mr("+"),
  new MathSum({ children: [sub("w", "k"), fn("logit", [sub("p", "k"), mr("(x)")])], subScript: [mr("k=1")], superScript: [mr("K")] })] })]));
add(P("where the weights are fitted by logistic regression on a held-out validation split. Segments whose score exceeds a threshold tuned for maximum validation F1 (0.408) are replaced by a quarantine marker before the agent sees them.", { noIndent: true }));

const g = (t) => ({ t, align: AlignmentType.LEFT });
add(Tbl("Behavioural Features of a Proposed Tool Call", [880, 1540, 2620],
  [[g("**Group**"), g("**Feature**"), g("**Description**")]],
  [
    [g("Alignment"), g("`goal_sim`"), g("similarity of call and user goal")],
    [g(""), g("`name_overlap`"), g("tool-name tokens found in the goal")],
    [g(""), g("`toolkit_in_goal`"), g("toolkit mentioned in the goal")],
    [g("Drift"), g("`obs_sim`"), g("max similarity to untrusted segments")],
    [g(""), g("`sim_suspicious`"), g("similarity to top-scored segment")],
    [g(""), g("`drift`"), g("difference of similarities, Eq. (3)")],
    [g(""), g("`susp_overlap`"), g("token overlap with top-scored segment")],
    [g("Provenance"), g("`arg_from_user`"), g("argument values present in goal")],
    [g(""), g("`arg_from_obs_only`"), g("taint ratio, Eq. (4)")],
    [g(""), g("`new_contact`"), g("recipient/account absent from goal")],
    [g(""), g("`n_atoms`"), g("number of argument values")],
    [g("Capability"), g("`risk_level`"), g("read / write / high-risk tool verb")],
    [g(""), g("`outbound`"), g("send, share, post, transfer, …")],
    [g(""), g("`exfil_flow`"), g("outbound payload read from tools")],
    [g(""), g("`new_toolkit`"), g("first use of an unrelated toolkit")],
    [g("Context"), g("`obs_inj_max`"), g("max Layer-1 score of observations")],
    [g(""), g("`obs_inj_last`"), g("Layer-1 score of last observation")],
    [g(""), g("`step`"), g("number of previous tool calls")],
  ]));
add(H2("Layer 2: Behavioural Monitor"));
add(P("For every proposed call *a*_{t} the monitor computes the features in Table I using only information available at that moment. Let *e*(·) be the unit-norm MiniLM embedding, *d*(*a*_{t}) a textual rendering of the call (tool name, tool description and argument values), *e*_{a} = *e*(*d*(*a*_{t})), *e*_{g} = *e*(*g*), *e*_{s} = *e*(*s*), and *S*_{<t} the set of untrusted segments observed so far. Drift compares the call with what was read and with what was asked:"));
add(Eq([mr("Δ("), sub("a", "t"), mr(")="),
  fn(new MathLimitLower({ children: [mr("max")], limit: [mr("s∈"), sub("S", "<t")] }),
    [fn("cos", [new MathRoundBrackets({ children: [sub("e", "a"), mr(","), sub("e", "s")] })])]),
  mr("−"), fn("cos", [new MathRoundBrackets({ children: [sub("e", "a"), mr(","), sub("e", "g")] })])]));
add(P("A positive drift means the action resembles something the agent read more than what the user requested. Argument provenance is captured by a taint ratio over the atomic values *X*(*a*_{t}) in the arguments (e-mail addresses, account numbers, identifiers and content words):", { noIndent: true }));
add(Eq([mr("ρ("), sub("a", "t"), mr(")="), new MathFraction({
  numerator: [mr("|{x∈X("), sub("a", "t"), mr("): x∉g ∧ x∈"), sub("O", "<t"), mr("}|")],
  denominator: [mr("|X("), sub("a", "t"), mr(")|")] })]));
add(P("where *O*_{<t} is the concatenated text of previous observations. Capability features encode whether the tool reads, writes or performs a high-risk or outbound operation, and an exfiltration feature measures how much of an outbound call's payload was read from earlier tool outputs. Layer-1 scores of previous observations are included as context. An XGBoost classifier (400 trees, depth 4, learning rate 0.05) maps the 18-dimensional vector to *P*(hijacked), and calls with probability of at least 0.5 are blocked.", { noIndent: true }));


add(H2("Layer 3: Runtime Guard and Security Alerting"));
add(P("Algorithm 1 summarises the interception logic. In *prevent* mode a blocked call is not executed and the agent receives an error listing human-readable reasons derived from the features (for example, “sends to a recipient the user never mentioned”); in *detect* mode calls proceed and only alerts are raised. Alerts are graded: MEDIUM when injected content is quarantined, HIGH when a call is blocked, and CRITICAL when the blocked call is high-risk and shows exfiltration, an unknown recipient or tainted arguments. A CRITICAL alert, or two HIGH alerts in one session, triggers a *session lockdown* in which further write or high-risk calls are refused until a human reviews the session. All decisions are appended to a JSON-lines audit log suitable for ingestion by a security information and event management (SIEM) system."));
{
  const L = (n, t, ind = 0) => new Paragraph({ indent: { left: 200 + ind * 220, hanging: 200 }, spacing: { after: 0 },
    children: [new TextRun({ text: n ? `${n}: ` : "", font: FONT, size: 16 }), ...runs(t, { size: 16 })] });
  const cell = new TableCell({
    width: { size: COL, type: WidthType.DXA }, margins: { top: 40, bottom: 60, left: 80, right: 80 },
    borders: { top: none, bottom: none, left: none, right: none },
    children: [
      L("", "**Input:** user goal *g*, tool *f*, proposed call *a*_{t} = (τ, θ), history *H*_{t}"),
      L("1", "*x* ← features(*a*_{t} | *g*, *H*_{t})   ▷ Layer 2"),
      L("2", "**if** session locked **and** risk(τ) ≥ write **then** alert(HIGH); **return** error"),
      L("3", "*p* ← XGBoost(*x*)"),
      L("4", "**if** *p* ≥ 0.5 **then**"),
      L("5", "alert(HIGH or CRITICAL); lockdown if required", 1),
      L("6", "**return** error with reasons", 1),
      L("7", "*o* ← *f*(θ)   ▷ execute the tool"),
      L("8", "**for each** segment *s* ∈ segments(*o*) **do**   ▷ Layer 1"),
      L("9", "**if** ŝ(*s*) ≥ 0.408 **then** *o* ← quarantine(*o*, *s*); alert(MEDIUM)", 1),
      L("10", "append (*a*_{t}, raw *o*) to *H*_{t}; **return** sanitised *o*"),
    ],
  });
  const head = new TableCell({
    width: { size: COL, type: WidthType.DXA }, margins: { top: 30, bottom: 30, left: 80, right: 80 },
    borders: { top: none, left: none, right: none, bottom: { style: BorderStyle.SINGLE, size: 4, color: "000000" } },
    children: [new Paragraph({ children: runs("**Algorithm 1:** Tool-call interception by the runtime guard", { size: 16 }) })],
  });
  add(new Paragraph({ spacing: { before: 120, after: 0 }, children: [] }));
  add(new Table({ width: { size: COL, type: WidthType.DXA }, columnWidths: [COL],
    borders: { top: { style: BorderStyle.SINGLE, size: 8, color: "000000" }, bottom: { style: BorderStyle.SINGLE, size: 8, color: "000000" },
      left: none, right: none, insideHorizontal: none, insideVertical: none },
    rows: [new TableRow({ cantSplit: true, children: [head] }), new TableRow({ cantSplit: true, children: [cell] })] }));
  add(new Paragraph({ spacing: { after: 120 }, children: [] }));
}

add(H1("Experimental Setup"));
add(H2("Text Corpora"));
add(P("Table II lists the Kaggle datasets used for Layer 1. Texts were whitespace-normalised and de-duplicated case-insensitively across all sources, and texts that appeared with contradicting labels were removed. This left 69,072 texts (35.1% injections), split 70/10/20 into training, validation and test sets stratified by source and label. A fourth Kaggle dataset, written independently, was held out entirely as an out-of-distribution (OOD) test set of 586 texts (485 attacks). Because the two transformer detectors run on a CPU at about nine texts per second, they were evaluated on a stratified sample of 5,000 test texts, and a stratified sample of 3,001 validation texts was used to fit the stacker; all models are compared on identical texts."));
add(Tbl("Kaggle Datasets Used for Content Detection", [1720, 1960, 760, 600],
  [["**Dataset**", { t: "**Content**", align: AlignmentType.LEFT }, "**Texts**", "**Inj.**"]],
  [
    ["AI Agent Cybersecurity 2026 {@kg_chuneeb}", { t: "S-Labs and deepset injections", align: AlignmentType.LEFT }, "11,267", "4,785"],
    ["Prompt Injection & Jailbreak Detection {@kg_krish}", { t: "JailbreakHub, Alpaca, deepset lineage", align: AlignmentType.LEFT }, "18,855", "108"],
    ["Malicious Prompt Detection (MPDD) {@kg_mpdd}", { t: "malicious and benign prompts", align: AlignmentType.LEFT }, "38,950", "19,336"],
    ["LLM Prompt Injection Classification {@kg_abdul}", { t: "six attack categories; OOD test only", align: AlignmentType.LEFT }, "586", "485"],
  ], "Counts after cross-dataset de-duplication; duplicates are attributed to the first source."));
add(H2("Benchmark Models"));
add(P("Two prompt-injection detectors hosted on Kaggle Models were evaluated without fine-tuning: a mirror of ProtectAI's DeBERTa-v3-base detector {@protectai} and Wolf Defender {@wolf}. Meta's Llama Prompt Guard (86M) {@promptguard} is also hosted on Kaggle but is licence-gated and was not included. Inputs were truncated to 512 tokens."));
add(H2("Agent Traces"));
add(P("We converted InjecAgent {@injecagent} into multi-step traces of user goal, tool calls and observations. For each pair of a user case (17) and an attacker case (62: 30 direct-harm and 32 data-stealing) we generate the five scenarios of Table III. Injected observations are taken verbatim from InjecAgent in its base and enhanced variants; clean observations replace the injection slot with benign texts from the Layer-1 test split. Attacker-tool arguments are derived from the attacker instruction, and data-stealing traces read private data using InjecAgent's simulated tool responses before calling *GmailSendEmail* with that data. Scenarios D and E are hard negatives: the user explicitly requests the same sensitive actions with identical tools and arguments, so a monitor that relies on tool type alone must fail. In total there are 8,432 traces with 16,428 tool calls, of which 3,196 are hijacked."));
add(Tbl("Agent Trace Scenarios Derived from InjecAgent", [1400, 1980, 620, 1040],
  [["**Scenario**", { t: "**Description**", align: AlignmentType.LEFT }, "**Traces**", "**Calls (hij.)**"]],
  [
    ["A. Benign", { t: "clean output, user task only", align: AlignmentType.LEFT }, "1,054", "1,054 (0)"],
    ["B. Injected, resisted", { t: "injection present, agent ignores it", align: AlignmentType.LEFT }, "2,108", "2,108 (0)"],
    ["C. Injected, hijacked", { t: "agent executes attacker calls", align: AlignmentType.LEFT }, "2,108", "5,304 (3,196)"],
    ["D. Benign sensitive", { t: "user requests the attacker's actions", align: AlignmentType.LEFT }, "1,054", "2,652 (0)"],
    ["E. Injected + legitimate", { t: "injection present; user requests another sensitive task", align: AlignmentType.LEFT }, "2,108", "5,310 (0)"],
  ]));
add(H2("Protocols, Baselines and Implementation"));
add(P("Layer 2 is evaluated with grouped five-fold cross-validation in two settings: *unseen attacker goals*, where all traces of an attacker case fall in the same fold (scenario E pairs cases within a fold), and *unseen user tasks*, where folds are formed by user tool. Baselines are a rule that blocks any non-first write or high-risk call after a Layer-1 flag; logistic regression on Layer-1 context scores only; an unsupervised Isolation Forest {@iforest} trained on benign calls with a 3% false-alarm budget; XGBoost on behavioural features without Layer-1 context; and logistic regression and random forest on all features. End-to-end results use out-of-fold scores from the unseen-attacker-goal setting. All experiments ran on a 12-core CPU without a GPU using scikit-learn {@sklearn}, XGBoost {@xgboost}, PyTorch and Hugging Face Transformers."));

add(H1("Results"));
add(H2("Layer 1: Content Detection"));
add(P("Table IV and Fig. 2 summarise content detection. The benchmark detectors transfer well to the OOD dataset (F1 0.925 and 0.948) but lose recall on the mixed in-distribution test set (0.754 and 0.641), which contains long jailbreak prompts and harmful requests outside their training focus. The trained models show the opposite pattern: TF-IDF is the strongest single model in-distribution (F1 0.946) but drops to 0.833 OOD. The stacked ensemble is best on both test sets (F1 0.954 and 0.968; ROC-AUC 0.984 and 0.999) because it combines complementary errors; its logit weights are 0.69 (TF-IDF), 0.39 (MiniLM), 0.09 (DeBERTa) and 0.05 (Wolf Defender). On the full 13,815-text test split the trained models reproduce their sample scores (F1 0.946 and 0.937). With only 101 benign OOD texts, OOD false-positive rates are coarse and are not emphasised."));
add(Tbl("Content Detection Results (Thresholds Tuned on Validation)", [1620, 570, 570, 570, 570, 570, 570],
  [[{ t: "" }, { t: "**In-distribution test**", span: 4 }, { t: "**OOD test**", span: 2 }],
   ["**Model**", "**P**", "**R**", "**F1**", "**AUC**", "**F1**", "**AUC**"]],
  [
    ["ProtectAI DeBERTa-v3^{a}", "0.861", "0.754", "0.804", "0.891", "0.925", "0.944"],
    ["Wolf Defender^{a}", "0.938", "0.641", "0.762", "0.814", "0.948", "1.000"],
    ["TF-IDF + LR", "0.978", "0.916", "0.946", "0.983", "0.833", "0.991"],
    ["MiniLM + XGBoost", "0.959", "0.916", "0.937", "0.977", "0.919", "0.991"],
    ["**Stacked ensemble**", "0.964", "**0.944**", "**0.954**", "**0.984**", "**0.968**", "0.999"],
  ], "^{a}Kaggle benchmark model, zero-shot. Test: stratified sample of 5,000 texts; OOD: 586 texts."));
add(Figure("fig2_layer1_f1.png", "F1-score of the content detectors on the in-distribution test sample and the unseen OOD Kaggle dataset. Models marked * are Kaggle benchmark detectors.", 3.05));

add(H2("Layer 2: Behavioural Detection"));
add(P("Table V and Fig. 3 report hijacked-call detection. Layer-1 context alone is a weak predictor (F1 0.333): the same injected observation precedes both hijacked calls (scenario C) and legitimate calls (scenario E), and polite injections often receive low text scores. The rule baseline blocks many legitimate sensitive calls (false-positive rate 18.5%). Isolation Forest reaches F1 0.876 without labels, confirming that hijacked calls are behavioural outliers. The supervised monitor achieves F1 0.993 with a 0.28% false-positive rate on unseen attacker goals and F1 0.995 with 0.04% on unseen user tasks. Removing Layer-1 context leaves performance essentially unchanged (F1 0.993), showing that decisions are driven by behaviour rather than by text. Per scenario, the monitor flags 0.53% of legitimate calls in hard-negative scenario D and 0.43% in E, none in A and B, and detects 99.66% of hijacked calls in C. Fig. 4 shows that the most informative features are similarity to the most suspicious segment, overlap between tool name and goal, and drift, followed by argument provenance."));
add(Tbl("Hijacked Tool-Call Detection (Grouped Cross-Validation)", [1500, 590, 590, 590, 690, 1080],
  [[{ t: "" }, { t: "**Unseen attacker goals**", span: 4 }, { t: "**Unseen tasks**" }],
   ["**Model**", "**P**", "**R**", "**F1**", "**FPR**", "**F1**"]],
  [
    ["Rule baseline", "0.450", "0.627", "0.524", "18.5%", "0.524"],
    ["Text scores only (LR)", "0.434", "0.269", "0.333", "8.5%", "0.348"],
    ["Isolation Forest", "0.846", "0.908", "0.876", "4.0%", "0.872"],
    ["Behaviour only (XGB)", "0.990", "0.996", "0.993", "0.25%", "0.995"],
    ["All features (LR)", "0.982", "0.994", "0.988", "0.43%", "0.990"],
    ["All features (RF)", "0.982", "0.997", "0.990", "0.43%", "0.997"],
    ["**Proposed (XGB)**", "0.989", "0.997", "**0.993**", "0.28%", "0.995"],
  ]));
add(Figure("fig3_layer2_f1.png", "F1-score and false-positive rate (FPR) of hijacked tool-call detection on attacker goals unseen during training.", 3.05));
add(Figure("fig4_importance.png", "Ten most important behavioural features of the proposed XGBoost monitor (share of total split gain).", 3.05));

add(H2("End-to-End Prevention"));
add(P("Table VI combines both layers using out-of-fold scores. Without defence every hijacked trajectory succeeds by construction. Layer-1 sanitisation alone stops all enhanced attacks, whose “IMPORTANT!!! Ignore all previous instructions” prefix is easily detected, but only 66.8% of base attacks: polite instructions such as “Please retrieve my saved addresses … and email them to amy.watson@gmail.com” receive an ensemble score of 0.058. Layer 2 alone prevents 99.91% of hijacked trajectories. The full guard prevents all of them while 99.1% of benign traces complete with no false block and no wrongly quarantined output; in the hardest scenario D utility is 97.8%. Fig. 5 shows the trade-off as the blocking threshold varies: prevention remains at 100% up to a threshold of 0.85 while utility rises from 98.0% to 99.7%."));
add(Tbl("Attack Success Rate and Utility (Unseen Attacker Goals)", [1800, 1080, 1080, 1080],
  [["**Defence**", "**ASR base**", "**ASR enh.**", "**Utility**"]],
  [
    ["No defence", "100%", "100%", "100%"],
    ["Layer 1 only (sanitise)", "33.2%", "0.0%", "99.7%"],
    ["Layer 2 only (block)", "0.09%", "0.09%", "99.4%"],
    ["**Layer 1 + Layer 2**", "**0.0%**", "**0.0%**", "99.1%"],
  ]));
add(Figure("fig5_tradeoff.png", "Attack prevention rate and benign task utility of the full guard as a function of the Layer-2 blocking threshold.", 3.05));

add(H2("Case Study and Overhead"));
add(P("In the interactive demonstrator a user asks the agent for laptop details, and a review in the tool output asks the agent to retrieve the user's saved addresses and e-mail them to an external address. Layer 1 scores the review 0.058 and lets it through. When the agent then calls *AmazonView​SavedAddresses*, Layer 2 assigns a risk of 0.998, because the call resembles the review (similarity 0.55) far more than the goal (0.06), and blocks it; the subsequent *GmailSendEmail* to the unseen recipient scores 1.00 and raises a CRITICAL alert followed by session lockdown. Conversely, an identical $3,000 transfer to the same account is blocked (risk 1.00) when it originates from an injected e-mail and allowed (risk 0.00) when the user requests it, showing that the guard reasons about provenance rather than action type."));
add(P("Layer 2 adds about 25 ms per tool call on a CPU (median, including embedding). Layer-1 cost is dominated by the two transformer detectors (about nine segments per second on a CPU); a deployment can run them on a GPU or rely on the TF-IDF and MiniLM members, which alone reach F1 0.946 and 0.937."));

add(H1("Discussion and Limitations"));
add(P("**Simulated actions.** Hijacked calls were constructed from InjecAgent attacker instructions with a deterministic argument extractor rather than generated by a live LLM. Real agents paraphrase, interleave steps and comply partially, so the near-perfect Layer-2 scores should be read as an upper bound; evaluation with live agents on dynamic benchmarks such as AgentDojo {@agentdojo} is the most important next step."));
add(P("**Adaptive attackers.** An attacker aware of the monitor may align the injected task with the user's goal, for instance by changing only the recipient of an e-mail the user asked to send. Provenance features (`new_contact`, taint) target exactly this case, but evaluation against adaptive attacks remains open."));
add(P("**Scope of the Layer-1 evaluation.** The transformer detectors were scored on a 5,000-text sample because of CPU limits, and they may have been trained on some of the same public sources. The OOD dataset is small and attack-heavy."));
add(P("**Complementarity.** The guard does not replace design-level isolation such as CaMeL {@camel}; it is a drop-in layer for existing agents that also provides observability through graded alerts and audit logs. All data used are public, and no attacks were executed against real systems."));

add(H1("Conclusion"));
add(P("Runtime behavioural analysis of tool calls closes much of the gap left by text-only prompt-injection detectors. A stacked ensemble of Kaggle benchmark detectors and trained classifiers improves content detection (F1 0.954 in-distribution and 0.968 OOD), and a behavioural monitor built on goal alignment, drift and provenance detects hijacked tool calls with F1 0.993 on unseen attacker goals while sparing legitimate sensitive actions. Together with graded alerts and session lockdown, the guard prevented all hijacked trajectories in our evaluation with 99.1% benign utility. Future work will evaluate the guard with live LLM agents, multi-turn and multimodal injections and adaptive attacks, and will combine it with design-level defences."));

add(H1u("Acknowledgment"));
add(P("The authors thank [[guide / institution name]] for guidance and support. The implementation, trained models and interactive demonstrator are available at [[repository URL]]."));

// ------------------------------------------------------------------ references (in order of first citation)
add(H1u("References"));
order.forEach((k, i) => add(new Paragraph({
  alignment: AlignmentType.LEFT, indent: { left: 360, hanging: 360 }, spacing: { after: 0 },
  tabStops: [{ type: TabStopType.LEFT, position: 360 }],
  children: [new TextRun({ text: `[${i + 1}]\t`, font: FONT, size: 16 }), ...runs(curly(REFS[k]), { size: 16 })],
})));
const unused = Object.keys(REFS).filter((k) => !order.includes(k));
if (unused.length) console.warn("uncited references:", unused.join(", "));

// ------------------------------------------------------------------ document
const margins = { top: 1080, bottom: 1440, left: 900, right: 900 };
const doc = new Document({
  creator: "", title: "Runtime Detection and Prevention of Prompt Injection Attacks in Autonomous LLM Agents Using Behavioural Analysis",
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 20, color: "000000" }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 20, italics: true, color: "000000" }, paragraph: { outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 200 } } } }] }] },
  sections: [
    { properties: { page: { size: { width: 12240, height: 15840 }, margin: margins } },
      children: [title, authors, new Paragraph({ spacing: { after: 200 }, children: [] })] },
    { properties: { type: SectionType.CONTINUOUS, page: { size: { width: 12240, height: 15840 }, margin: margins },
        column: { count: 2, space: 360, equalWidth: true } },
      children: body },
  ],
});
// Word renders math runs italic; function names must be upright (m:sty = plain)
const JSZip = require("jszip");
Packer.toBuffer(doc).then(async (raw) => {
  const zip = await JSZip.loadAsync(raw);
  let xml = await zip.file("word/document.xml").async("string");
  xml = xml.replace(/<m:r><m:t>(ASR|cos|max|logit)<\/m:t>/g, '<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>$1</m:t>');
  zip.file("word/document.xml", xml);
  const b = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  fs.writeFileSync(OUT, b); console.log("wrote", OUT, `(${order.length} references, ${figN} figures, ${tabN} tables, ${eqN} equations)`); });
