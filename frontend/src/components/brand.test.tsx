import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Brand } from "./brand";

it("uses the owl emoji as the Knowli mark", () => {
  render(<Brand label="Knowli" />);

  expect(screen.getByText("🦉")).toBeInTheDocument();
});
