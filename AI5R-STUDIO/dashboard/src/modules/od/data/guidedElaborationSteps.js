/**
 * The small, fixed set of follow-up questions Open Design asks after the
 * initial Mission Input, per OD-001's Guided Elaboration design — one
 * focused question per step, never a long form.
 */
const guidedElaborationSteps = [
  {
    key: "identity",
    question: "Who is this business, and what industry are you in?",
    placeholder: "e.g. a boutique pump maintenance company serving industrial clients",
  },
  {
    key: "objective",
    question: "What does success look like once this is working?",
    placeholder: "e.g. every service request handled without me chasing anyone",
  },
];

export default guidedElaborationSteps;
