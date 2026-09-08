export type StepperProps = { steps: readonly string[]; current: number; label: string };

export function Stepper({ steps, current, label }: StepperProps) {
  return <ol className="docly-stepper" aria-label={label}>{steps.map((step, index) => <li key={`${index}-${step}`} aria-current={current === index ? 'step' : undefined} data-complete={index < current ? 'true' : undefined}><span className="docly-stepper__number" aria-hidden="true">{index + 1}</span><span>{step}</span></li>)}</ol>;
}
