import { useState } from "react";
import { SelectField } from "../../shared/ui";
import type { Program } from "./api";

export function filterPrograms(
  programs: Program[],
  school: string,
  schedule: string,
) {
  return programs.filter(
    (p) =>
      (!school || String(p.school_id ?? "") === school) &&
      (!schedule || String(p.schedule_id ?? "") === schedule),
  );
}

export function ProgramSelector({
  id,
  label,
  programs,
  value,
  onChange,
  disabled = false,
  emptyLabel = "Seleccione un programa",
}: {
  id: string;
  label: string;
  programs: Program[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  emptyLabel?: string;
}) {
  const [school, setSchool] = useState("");
  const [schedule, setSchedule] = useState("");
  const schools = [
    ...new Map(
      programs
        .filter((p) => p.school_id !== null && p.school)
        .map((p) => [
          p.school_id,
          { value: String(p.school_id), label: p.school! },
        ]),
    ).values(),
  ];
  const schedules = [
    ...new Map(
      filterPrograms(programs, school, "")
        .filter((p) => p.schedule_id !== null && p.schedule)
        .map((p) => [
          p.schedule_id,
          { value: String(p.schedule_id), label: p.schedule! },
        ]),
    ).values(),
  ];
  const available = filterPrograms(programs, school, schedule);
  function update(nextSchool: string, nextSchedule: string) {
    if (
      !filterPrograms(programs, nextSchool, "").some(
        (p) => String(p.schedule_id ?? "") === nextSchedule,
      )
    )
      nextSchedule = "";
    setSchool(nextSchool);
    setSchedule(nextSchedule);
    if (
      value &&
      !filterPrograms(programs, nextSchool, nextSchedule).some(
        (p) => String(p.program_id) === value,
      )
    )
      onChange("");
  }
  const current = programs.find((p) => String(p.program_id) === value);
  const options = available.map((p) => ({
    value: String(p.program_id),
    label: p.name + (p.schedule ? " · " + p.schedule : ""),
  }));
  if (current && !options.some((p) => p.value === value))
    options.push({ value, label: current.name + " · seleccionado" });
  return (
    <div className="agents-program-selector">
      <div className="agents-form-grid">
        <SelectField
          id={id + "-school"}
          label="Escuela"
          disabled={disabled}
          value={school}
          options={[{ value: "", label: "Todas las escuelas" }, ...schools]}
          onChange={(e) => update(e.target.value, schedule)}
        />
        <SelectField
          id={id + "-schedule"}
          label="Jornada"
          disabled={disabled}
          value={schedule}
          options={[{ value: "", label: "Todas las jornadas" }, ...schedules]}
          onChange={(e) => update(school, e.target.value)}
        />
      </div>
      <SelectField
        id={id}
        label={label}
        disabled={disabled}
        value={value}
        options={[{ value: "", label: emptyLabel }, ...options]}
        onChange={(e) => onChange(e.target.value)}
      />
      <small>{available.length} programas en la selección.</small>
    </div>
  );
}
