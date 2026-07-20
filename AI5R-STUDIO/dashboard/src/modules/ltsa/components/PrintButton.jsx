import { Button } from "../../../design-system";

/**
 * Triggers the browser's native print dialog, which is also how the user
 * saves the report as a PDF ("Print" -> "Save as PDF") — no PDF library
 * is introduced. Marked `no-print` so the button itself never appears in
 * the printed/exported output.
 */
export default function PrintButton() {
  return (
    <Button className="no-print" onClick={() => window.print()}>
      Print / Save as PDF
    </Button>
  );
}
