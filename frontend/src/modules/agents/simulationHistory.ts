export function simulationHistory(value: string) {
  const messages: { role: "user" | "assistant"; content: string }[] = [];
  for (const line of value.split(/\r?\n/)) {
    const heading = /^(Cliente|Asesor):\s*(.*)$/i.exec(line.trimStart());
    if (heading) {
      messages.push({
        role: heading[1].toLowerCase() === "cliente" ? "user" : "assistant",
        content: heading[2],
      });
    } else if (line.trim()) {
      const previous = messages.at(-1);
      if (!previous)
        throw Error("Identifica cada intervención con Cliente: o Asesor:.");
      previous.content += "\n" + line;
    }
  }
  if (messages.length > 12)
    throw Error("El historial de prueba admite hasta 12 intervenciones.");
  for (const message of messages) {
    message.content = message.content.trim();
    if (!message.content || message.content.length > 1600)
      throw Error("Cada intervención debe tener entre 1 y 1600 caracteres.");
  }
  return messages;
}
