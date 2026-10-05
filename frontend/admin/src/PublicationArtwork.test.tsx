import { render } from "@testing-library/react";
import { expect, it } from "vitest";
import { PublicationArtwork } from "./PublicationArtwork";
import fixture from "../../shared/publication-template.fixture.json";
import type { PublicationTemplate } from "../../shared/publications";

it("centers every B field and CTA while retaining legacy A alignment", () => {
  const fields = { kicker: "CASPER LOTO", title: "Общее достижение", value: "1 000 000", description: "Выигрышные билеты", fact: "За всю историю" };
  const template = { ...fixture, textAlign: "center" } as PublicationTemplate;
  const { container, rerender } = render(<PublicationArtwork template={template} fields={fields} />);
  const nodes = [...container.querySelectorAll("svg > text")];
  expect(nodes).toHaveLength(6);
  expect(nodes.every(node => node.getAttribute("text-anchor") === "middle")).toBe(true);
  for (const [index, box] of Object.values(template.formats.story.zones).entries()) {
    expect(Number(nodes[index].getAttribute("x"))).toBe(box[0] + box[2] / 2);
  }
  rerender(<PublicationArtwork template={fixture as PublicationTemplate} fields={fields} />);
  expect([...container.querySelectorAll("svg > text")].every(node => node.getAttribute("text-anchor") === "start")).toBe(true);
});
