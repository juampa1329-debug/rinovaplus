import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { InstitutionContacts } from "../institution/InstitutionContacts";
import { MessageDelivery } from "../institution/InboxDelivery";
import { ErrorFeedbackContext } from "../institution/ErrorFeedback";

it("keeps public call and WhatsApp contacts separate and only prepares a draft", () => {
  const change = vi.fn();
  render(
    <InstitutionContacts
      value={[
        {
          label: "Admisiones",
          number: "+573004714060",
          use: "calls",
          active: true,
          note: "",
        },
      ]}
      onChange={change}
    />,
  );
  expect(screen.getByRole("combobox", { name: "Uso autorizado" })).toHaveValue(
    "calls",
  );
  fireEvent.change(screen.getByRole("combobox", { name: "Uso autorizado" }), {
    target: { value: "whatsapp" },
  });
  expect(change.mock.lastCall?.[0][0].use).toBe("whatsapp");
  expect(screen.getByText(/no conectan un canal/i)).toBeInTheDocument();
});

it("explains a cancelled response without retrying or sending it", () => {
  const report = vi.fn();
  render(
    <ErrorFeedbackContext.Provider value={report}>
      <MessageDelivery
        state="cancelled"
        reason="gemini_reply_context_changed"
      />
    </ErrorFeedbackContext.Provider>,
  );
  fireEvent.click(
    screen.getByRole("button", { name: /Cancelado · ver motivo/ }),
  );
  expect(report.mock.calls[0][0].code).toBe("gemini_reply_context_changed");
  expect(report).toHaveBeenCalledTimes(1);
});
