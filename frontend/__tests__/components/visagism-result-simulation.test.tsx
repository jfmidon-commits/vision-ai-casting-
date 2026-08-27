import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { VisagismResultView } from "@/components/visagism/visagism-result";
import { analysisApi } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  analysisApi: {
    listVisagismSimulations: jest.fn(),
    getVisagismBarberBrief: jest.fn(),
    simulateVisagism: jest.fn(),
  },
}));

const mockedApi = analysisApi as jest.Mocked<typeof analysisApi>;

const haircuts = [
  "Quiff texturizado",
  "Side Part com volume no topo",
  "Pompadour moderado",
  "Undercut com topo alongado",
  "Crew Cut com laterais mais baixas",
];

function brief(name: string) {
  return {
    recommendation_name: name,
    grounded_in: ["formato facial: redondo", "densidade do cabelo: média"],
    top: `Topo para ${name}`,
    sides: `Laterais para ${name}`,
    back: `Parte de trás para ${name}`,
    fringe: `Franja para ${name}`,
    texture: "Textura natural",
    finish: "Acabamento natural",
    avoid: "Evitar volume lateral excessivo",
    note: "Sem medidas inventadas.",
  };
}

const result = {
  face_shape_category: "round",
  recommended_hairstyles: haircuts,
  primary_hairstyle: haircuts[0],
  interpretation: {
    status: "ready",
    executive_summary: "A recomendação principal é Quiff texturizado.",
    current_hair_assessment: {
      summary: "Cabelo analisado.",
      strengths: [],
      attention_points: [],
    },
    primary_recommendation: {
      name: haircuts[0],
      why_it_works: "Ajuda a alongar visualmente o rosto.",
      visual_effect: "Mais altura no topo.",
      professional_positioning: "Versátil.",
      maintenance_level: "médio",
      barber_instruction: "Ajustar ao cabelo real.",
    },
    alternative_hairstyles: haircuts.slice(1).map((name) => ({
      name,
      why_it_works: `Motivo para ${name}`,
      best_use_case: "Alternativa estética.",
      maintenance_level: "avaliar com o profissional",
    })),
    barber_brief: brief(haircuts[0]),
    professional_image: {
      actor_casting: "Casting",
      commercial_model: "Comercial",
      corporate_institutional: "Corporativo",
      lifestyle_advertising: "Lifestyle",
    },
    limitations: [],
    confidence_note: "Boa base.",
  },
} as any;

function readySimulation(haircutName: string, cached = false) {
  return {
    analysis_id: "analysis-1",
    selected_haircut: haircutName,
    simulation_status: "ready",
    reason: null,
    provider_configured: true,
    ready_enabled: true,
    reference_count: 3,
    cached,
    barber_brief: brief(haircutName),
    card_media: {
      personPhoto: "https://example.test/original.jpg",
      displayImage: `https://example.test/${encodeURIComponent(haircutName)}.png`,
      realPhotoVerified: true,
      simulationApplied: true,
      identityVerified: true,
      fallbackUsed: false,
      displayMode: "validated_hair_overlay",
    },
  } as any;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedApi.listVisagismSimulations.mockResolvedValue({ data: { data: [] } } as any);
  mockedApi.getVisagismBarberBrief.mockImplementation(async (_id, haircutName) =>
    ({ data: { data: brief(haircutName) } }) as any
  );
});

describe("VisagismResultView P1 simulation", () => {
  it("shows the five grounded haircuts and never generates automatically", async () => {
    render(<VisagismResultView result={result} analysisId="analysis-1" onReset={jest.fn()} />);

    for (const haircut of haircuts) {
      expect(screen.getByRole("button", { name: haircut })).toBeInTheDocument();
    }
    expect(screen.getByRole("button", { name: haircuts[0] })).toHaveAttribute("aria-pressed", "true");

    await waitFor(() => expect(mockedApi.listVisagismSimulations).toHaveBeenCalledWith("analysis-1"));
    expect(mockedApi.simulateVisagism).not.toHaveBeenCalled();
  });

  it("generates only the selected alternative and updates the barber brief", async () => {
    const user = userEvent.setup();
    const selected = haircuts[1];
    mockedApi.simulateVisagism.mockResolvedValue({
      data: { data: readySimulation(selected) },
    } as any);

    render(<VisagismResultView result={result} analysisId="analysis-1" onReset={jest.fn()} />);

    await user.click(screen.getByRole("button", { name: selected }));
    await waitFor(() =>
      expect(mockedApi.getVisagismBarberBrief).toHaveBeenCalledWith("analysis-1", selected)
    );
    await waitFor(() => expect(screen.getByText(`Topo para ${selected}`)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Gerar prévia deste corte" }));

    await waitFor(() =>
      expect(mockedApi.simulateVisagism).toHaveBeenCalledWith("analysis-1", selected)
    );
    expect(mockedApi.simulateVisagism).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("button", { name: "Original" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Simulação" })).toBeInTheDocument();
    expect(
      screen.getByAltText(`Simulação visual do corte ${selected}`)
    ).toHaveAttribute("src", expect.stringContaining(encodeURIComponent(selected)));
  });

  it("reopens a cached simulation without another provider request", async () => {
    const cached = readySimulation(haircuts[0], true);
    mockedApi.listVisagismSimulations.mockResolvedValue({ data: { data: [cached] } } as any);
    const user = userEvent.setup();

    render(<VisagismResultView result={result} analysisId="analysis-1" onReset={jest.fn()} />);

    expect(await screen.findByRole("button", { name: "Ver prévia salva" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ver prévia salva" }));

    expect(mockedApi.simulateVisagism).not.toHaveBeenCalled();
    expect(await screen.findByText("Prévia salva recuperada")).toBeInTheDocument();
    expect(screen.getByAltText(`Simulação visual do corte ${haircuts[0]}`)).toBeInTheDocument();
  });

  it("keeps the original photo when the safety pipeline blocks generation", async () => {
    const user = userEvent.setup();
    mockedApi.simulateVisagism.mockResolvedValue({
      data: {
        data: {
          analysis_id: "analysis-1",
          selected_haircut: haircuts[0],
          simulation_status: "blocked",
          reason: "identity_lock_failed",
          provider_configured: true,
          ready_enabled: false,
          reference_count: 3,
          cached: false,
          barber_brief: brief(haircuts[0]),
          card_media: {
            personPhoto: "https://example.test/original.jpg",
            displayImage: "https://example.test/original.jpg",
            realPhotoVerified: true,
            simulationApplied: false,
            identityVerified: false,
            fallbackUsed: true,
            displayMode: "original_plus_spec",
          },
        },
      },
    } as any);

    render(<VisagismResultView result={result} analysisId="analysis-1" onReset={jest.fn()} />);
    await user.click(screen.getByRole("button", { name: "Gerar prévia deste corte" }));

    expect(await screen.findByText("Simulação bloqueada com segurança")).toBeInTheDocument();
    expect(screen.getByAltText("Foto original preservada")).toHaveAttribute(
      "src",
      "https://example.test/original.jpg"
    );
    expect(screen.getByText(/não preservou a identidade/i)).toBeInTheDocument();
  });
});
