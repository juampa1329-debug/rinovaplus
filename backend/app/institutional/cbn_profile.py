"""Small editorial review of public institutional sources; never a financial source."""

from uuid import NAMESPACE_URL, uuid5

REVIEWED = "2026-11-20"
ADMISSIONS_LOCATION = "Avenida del Libertador #13-45, frente a la Registraduría, Santa Marta"
REGISTRATION_URL = "https://siieplus.online/SIIEWebPlus/inscripciones"
PREICFES_REGISTRATION_URL = "https://siieplus.online/SIIEWEBPLUS/PreIcfes/Inscripcion.html"
REGISTRATION_POLICY = (
    "\nINSCRIPCIÓN REVISADA POR EL TITULAR (2026-11-24): cuando la persona manifieste que desea "
    "inscribirse o adelantar ese proceso, comparte el formulario oficial de las fuentes revisadas. "
    "Para PRE-ICFES usa su formulario específico; para los demás programas usa el formulario general, "
    "en el que la persona elige programa y jornada y completa sus datos. No intercambies ambos enlaces. "
    "Puede adelantar la inscripción mientras Contabilidad o Tesorería revisan un reajuste financiero; "
    "el formulario no aprueba el plan, confirma pagos, reserva un cupo ni acredita una matrícula. "
    "Si pide ayuda, consulta las fuentes inscripcion_ayuda y explica sólo el paso pertinente. "
    "Los datos y documentos se completan directamente en el sitio oficial, no se solicitan por este chat. "
    "No afirmes que lo llenaste, enviaste o que ya se confirmó una inscripción sin evidencia del sistema. "
    "Si ya compartiste el formulario, continúa desde ese trámite y sus dificultades; no reinicies una "
    "promoción o presentación general. Si confirmó interés, concreta el siguiente paso solicitado. "
    "Si dice haberlo completado, orienta a verificarlo antes de pedirlo de nuevo."
)
LOCATION_POLICY = (
    "\nUBICACIÓN Y ATENCIÓN PRESENCIAL REVISADAS POR EL TITULAR (2026-11-20): "
    "La oficina de Admisiones de CBN está en " + ADMISSIONS_LOCATION + ". "
    "Ésta es la ubicación confirmada para orientación presencial; no la confundas con una sede académica. "
    "No inventes otras direcciones, horarios, mapas ni disponibilidad de empleados. "
    "Una respuesta anterior del propio agente no es una fuente institucional: si contradice este dato, "
    "reconoce el error y corrígelo, sin insistir ni defenderla. "
    "Si preguntan por hablar personalmente, ofrece visitar la oficina y conversar con el equipo de Admisiones. "
    "No interpretes esa petición como una pregunta sobre tu identidad ni respondas con una presentación de asistente virtual. "
    "No prometas que encontrarán físicamente al nombre de atención de la IA, ni que ya concertaste una cita. "
    "Si preguntan expresamente si eres IA, responde con transparencia."
)
FACTS = [
    {
        "topic": "preicfes_volante_provisional",
        "reviewed_at": "2026-11-25",
        "source": "owner_reviewed:2026-11-25:preicfes-payment-slip-next-day",
        "text": (
            "INDICACIÓN OPERATIVA PROVISIONAL DEL TITULAR, sólo para PRE-ICFES: "
            "si la persona ya diligenció el formulario y pregunta cuándo pagar, indicarle que "
            "se le enviará el volante de pago al día siguiente. La gestión es manual del equipo "
            "mientras se integra y prueba el volante automático de SIIE. No afirmar que ya se "
            "generó o envió, ni que su inscripción o pago se corroboraron en SIIE sin un recibo. "
            "No inventar cuenta bancaria, enlace de pago, fecha de vencimiento ni exigir pago "
            "presencial. Esta indicación no modifica las tarifas ni las cuotas de la ficha."
        ),
    },
    {
        "topic": "inscripcion_general",
        "text": "Formulario oficial para adelantar la inscripción a los programas de CBN distintos de PRE-ICFES: " + REGISTRATION_URL + ". La persona elige programa y jornada y completa sus datos. No confirma por sí solo un pago, reajuste financiero, cupo o matrícula.",
        "source": REGISTRATION_URL,
        "reviewed_at": "2026-11-24",
    },
    {
        "topic": "inscripcion_preicfes",
        "text": "Formulario oficial exclusivo para la inscripción a PRE-ICFES CBN: " + PREICFES_REGISTRATION_URL + ". La persona completa sus datos y elige el grupo. PRE-ICFES conserva este formulario específico en lugar del formulario general de los otros programas.",
        "source": PREICFES_REGISTRATION_URL,
        "reviewed_at": "2026-11-24",
    },
    {
        "topic": "oficina_admisiones",
        "text": "Oficina de Admisiones: " + ADMISSIONS_LOCATION + ". Ubicación confirmada por el titular; no confirma horarios ni la presencia de un asesor específico.",
        "source": "owner_reviewed:2026-11-20:admissions-office",
    },
    {
        "topic": "institucion",
        "text": "La Corporación Bolivariana del Norte (CBN) es una entidad sin ánimo de lucro de Santa Marta, creada en1995, dedicada a educación para el trabajo y el desarrollo humano y formación de técnicos laborales por competencias.",
        "source": "https://cbn.edu.co/institucion/",
    },
    {
        "topic": "escuelas",
        "text": "Su web presenta escuelas de Salud, TIC, Gastronomía, Administración, Logística y Turismo, además del Centro de Idiomas y programas de extensión. La oferta, jornada y duración se confirman en la ficha vigente de cada programa.",
        "source": "https://cbn.edu.co/",
    },
    {
        "topic": "calidad",
        "text": "CBN publica renovación y ampliación de certificaciones de calidad otorgadas por ICONTEC y procesos de mejora continua. Describir formación de calidad y procesos certificados; no equiparar esa certificación con acreditación universitaria de alta calidad ni extenderla a cada programa sin su respaldo específico.",
        "source": "https://cbn.edu.co/cbn-renueva-certificacion-icontec-16-anos-de-calidad/",
    },
    {
        "topic": "practicas",
        "text": "CBN describe prácticas en empresas y entidades del sector productivo y acompañamiento institucional. La postulación tiene requisitos y selección de la entidad receptora. Confirmar la modalidad, los requisitos y la disponibilidad de cada programa; no prometer empresa, remuneración, plaza ni contratación automática.",
        "source": "https://cbn.edu.co/empresas/",
    },
    {
        "topic": "convenios",
        "text": "La institución informa alianzas en salud, hotelería, comercio, educación y otros sectores. Las páginas publican cifras diferentes de convenios: no dar un total ni un convenio específico vigente sin comprobación adicional.",
        "source": "https://cbn.edu.co/cbn-renueva-certificacion-icontec-16-anos-de-calidad/",
    },
]


def facts_for(question=None):
    from app.institutional.registration_guidance import FACTS as help_facts, relevant
    return [*FACTS, *(help_facts if relevant(question) else [])]


def reviewed_sources(sources, question=None):
    """Same approved facts in context, returned metadata and citation validation."""
    values = list(sources)
    known = {source["id"] for source in values}
    for fact in facts_for(question):
        reviewed_at = fact.get("reviewed_at", REVIEWED)
        identifier = str(uuid5(NAMESPACE_URL, "cbn-reviewed:" + reviewed_at + ":" + fact["topic"]))
        if identifier not in known:
            values.append({"id": identifier, "title": "CBN · fuente institucional revisada · " + fact["topic"],
                           "text": fact["text"], "provenance": fact["source"], "revision": reviewed_at,
                           "source_kind": "reviewed_institutional_fact", "financial_source": False})
            known.add(identifier)
    return values


def general_instructions():
    return (
        "Eres Juan, de atención de la Corporación Bolivariana del Norte (CBN). "
        "Orienta con cercanía y precisión a aspirantes y estudiantes. "
        "Ayuda a conocer la institución y elegir una formación acorde con su interés; "
        "no tomas decisiones de admisión ni confirmas pagos. "
        "CBN es una institución de educación para el trabajo y el desarrollo humano en Santa Marta, "
        "con trayectoria desde1995, formación práctica y procesos de calidad certificados según sus fuentes institucionales. "
        "Consulta la ficha revisada para duración, materias, modalidad, requisitos y opciones de pago. "
        "Si el mensaje, el anuncio o la publicación ya identifica el programa, continúa desde ese interés. "
        "Acompaña con una explicación breve, resuelve la inquietud y propone un siguiente paso sin presionar. "
        "Para prácticas y convenios explica las condiciones del programa; no garantices plaza, empresa, "
        "remuneración, empleo ni cifras de convenios sin evidencia. No equipares certificación ICONTEC "
        "con acreditación universitaria de alta calidad. "
        "Precio, cuota, abono, vigencia y fecha ausentes se confirman con Admisiones. "
        "No inventes importes ni afirmes que ya realizaste una gestión. "
        "Usa español colombiano respetuoso, mensajes breves por ideas completas y emojis discretos. "
        "Recuerda el contexto del mismo hilo, respeta correcciones y solicita sólo datos necesarios. "
        "Si solicitan una persona, deriva con el contexto; el control Humano detiene tus envíos. "
        "Juan es el nombre de atención del agente: si preguntan si eres IA, responde con transparencia."
    )


def recommended_delivery():
    return {
        "brief_responses": True,
        "split_responses": True,
        "wait_seconds": 60,
        "typing_ms": 1500,
        "fragment_delay_ms": 3000,
        "reply_min_chunk_delay_ms": 3000,
        "chars_per_message": 350,
        "show_typing": True,
        "human_reply_style_enabled": True,
    }
