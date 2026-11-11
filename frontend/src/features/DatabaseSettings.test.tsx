import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { DatabaseSettings } from "./DatabaseSettings";

const snapshot = {
  revision: 0,
  connection: {
    server: "sql.example.invalid",
    port: 1433,
    username: "reader",
    certificate_hostname: "sql.example.invalid",
    database: "",
  },
  has_password: false,
  source: "environment",
  review: null,
};
const review = {
  database: "HORARIOSSIIE",
  engine_major: 16,
  edition: "Express",
  compatibility_level: 160,
  table_count: 50,
  column_count: 437,
  relation_count: 41,
  missing_academic_tables: ["dbo.ACAspirante"],
  missing_crm_tables: ["crm.Contact"],
  sql2019_engine: false,
};
const response = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

afterEach(() => vi.restoreAllMocks());

it("discovers and saves a selected partial database without retaining the password", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response(snapshot))
    .mockResolvedValueOnce(response({ databases: ["HORARIOSSIIE"] }))
    .mockResolvedValueOnce(response({ review, revision: 1 }));
  const user = userEvent.setup();
  render(<DatabaseSettings />);
  await waitFor(() =>
    expect(screen.getByLabelText("Usuario SQL")).toHaveValue("reader"),
  );
  await user.type(screen.getByLabelText("Contraseña"), "synthetic-ui-secret");
  await user.click(screen.getByRole("button", { name: "Listar bases" }));
  await screen.findByRole("option", { name: "HORARIOSSIIE" });
  await user.selectOptions(
    screen.getByLabelText("Base de datos"),
    "HORARIOSSIIE",
  );
  await user.click(screen.getByRole("button", { name: "Guardar selección" }));
  await screen.findByText(
    "Selección verificada y guardada con credenciales cifradas.",
  );
  expect(screen.getByLabelText("Contraseña")).toHaveValue("");
  expect(screen.getByText(/Puede ser un fragmento/)).toBeInTheDocument();
  expect(
    screen.getByText(/Seleccionarla no activa CRM ni crea tablas/),
  ).toBeInTheDocument();
  const init = fetch.mock.calls[2][1];
  expect(init?.method).toBe("PUT");
  expect(JSON.parse(String(init?.body))).toMatchObject({
    database: "HORARIOSSIIE",
    password: "synthetic-ui-secret",
    revision: 0,
  });
  expect(init?.headers).toMatchObject({ "X-CRM-Local": "1" });
  expect(document.body.textContent).not.toContain("synthetic-ui-secret");
});

it("clears typed credentials when changing the server and reports a safe connection error", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response(snapshot))
    .mockResolvedValueOnce(response({ detail: "sql_connection_failed" }, 503));
  const user = userEvent.setup();
  render(<DatabaseSettings />);
  await waitFor(() =>
    expect(screen.getByLabelText("Usuario SQL")).toHaveValue("reader"),
  );
  await user.type(screen.getByLabelText("Contraseña"), "temporary-secret");
  await user.clear(screen.getByLabelText("Servidor o IP"));
  await user.type(
    screen.getByLabelText("Servidor o IP"),
    "other.example.invalid",
  );
  expect(screen.getByLabelText("Contraseña")).toHaveValue("");
  await user.type(screen.getByLabelText("Contraseña"), "new-secret");
  await user.click(screen.getByRole("button", { name: "Listar bases" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No se pudo conectar",
  );
  expect(
    screen.getByRole("button", { name: "Guardar selección" }),
  ).toBeDisabled();
});

it("discards the old schema after a fresh connection test", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      response({
        ...snapshot,
        connection: { ...snapshot.connection, database: "HORARIOSSIIE" },
        has_password: true,
      }),
    )
    .mockResolvedValueOnce(
      response({
        review,
        tables: [["dbo", "ACProgramas"]],
        columns: [
          ["dbo", "ACProgramas", "Id_Programa", "int", 4, 10, 0, false, 1],
        ],
        relations: [],
      }),
    )
    .mockResolvedValueOnce(
      response({ review: { ...review, table_count: 51 } }),
    );
  const user = userEvent.setup();
  render(<DatabaseSettings />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Ver estructura" }),
    ).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "Ver estructura" }));
  await user.selectOptions(
    await screen.findByLabelText("Tabla"),
    "dbo.ACProgramas",
  );
  expect(screen.getByText(/Id_Programa/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Probar conexión" }));
  await screen.findByText(/51 tablas visibles/);
  expect(screen.queryByLabelText("Tabla")).not.toBeInTheDocument();
  expect(screen.queryByText(/Id_Programa/)).not.toBeInTheDocument();
});
