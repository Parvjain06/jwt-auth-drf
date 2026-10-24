export default function Step({ n, title, lead, children }) {
  return (
    <section className="step" aria-labelledby={`step-${n}`}>
      <div className="step-rail" aria-hidden="true">
        <span className="step-num">{n}</span>
      </div>
      <div className="step-body">
        <h2 id={`step-${n}`}>{title}</h2>
        {lead && <p className="step-lead">{lead}</p>}
        {children}
      </div>
    </section>
  );
}
