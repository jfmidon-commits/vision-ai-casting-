import { render, screen } from "@testing-library/react";
import { IdentityLockedVisagismCard } from "@/components/visagism/identity-locked-visagism-card";

function baseAnalysis(cardMedia: any) {
  return {
    id: "analysis-1",
    status: "completed",
    card_media: cardMedia,
    visagism: { primary_recommendation: "Degradê baixo suave + topo texturizado" },
  };
}

describe("IdentityLockedVisagismCard", () => {
  it("refuses to render a normal card without verified real-person media", () => {
    render(<IdentityLockedVisagismCard analysis={baseAnalysis(undefined)} />);

    expect(screen.getByTestId("visagism-card-blocked")).toBeInTheDocument();
    expect(screen.queryByTestId("identity-locked-visagism-card")).not.toBeInTheDocument();
  });

  it("renders the original real photo when simulation is not approved", () => {
    render(
      <IdentityLockedVisagismCard
        analysis={baseAnalysis({
          personPhoto: "real-person.jpg",
          displayImage: "fake-generated-face.jpg",
          realPhotoVerified: true,
          realPhotoRefs: ["real-person.jpg", "real-side.jpg"],
          simulationApplied: true,
          identityVerified: false,
          displayMode: "validated_hair_beard_overlay",
        })}
      />,
    );

    const image = screen.getByTestId("visagism-display-image") as HTMLImageElement;
    expect(image.src).toContain("real-person.jpg");
    expect(screen.getByText("Foto original")).toBeInTheDocument();
  });

  it("allows a validated hair/beard overlay but keeps the original identity anchor", () => {
    render(
      <IdentityLockedVisagismCard
        analysis={baseAnalysis({
          personPhoto: "real-person.jpg",
          displayImage: "validated-overlay.jpg",
          realPhotoVerified: true,
          realPhotoRefs: ["real-person.jpg", "real-side.jpg", "real-three-quarter.jpg"],
          simulationApplied: true,
          identityVerified: true,
          displayMode: "validated_hair_beard_overlay",
        })}
      />,
    );

    const image = screen.getByTestId("visagism-display-image") as HTMLImageElement;
    expect(image.src).toContain("validated-overlay.jpg");
    expect(screen.getByTestId("original-anchor")).toHaveTextContent("real-person.jpg");
    expect(screen.getByText("Overlay cabelo/barba validado")).toBeInTheDocument();
  });

  it("blocks a personPhoto that is not one of the analysis inputs", () => {
    render(
      <IdentityLockedVisagismCard
        analysis={baseAnalysis({
          personPhoto: "other-person.jpg",
          displayImage: "other-person.jpg",
          realPhotoVerified: true,
          realPhotoRefs: ["real-person.jpg"],
          simulationApplied: false,
          identityVerified: false,
          displayMode: "original",
        })}
      />,
    );

    expect(screen.getByTestId("visagism-card-blocked")).toBeInTheDocument();
    expect(screen.getByText(/person_photo_must_come_from_analysis_inputs/)).toBeInTheDocument();
  });
});
