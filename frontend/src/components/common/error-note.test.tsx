import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { ApiError } from "@/lib/api";
import { ErrorNote } from "./error-note";

describe("error note", () => {
  it("translates API errors instead of exposing the server message", async () => {
    await i18n.changeLanguage("en");
    render(<ErrorNote error={new ApiError({ code: "model_unavailable", message: "internal provider detail" })} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Configure a model to use Ask.");
    expect(screen.queryByText("internal provider detail")).not.toBeInTheDocument();
  });
});
