import type { PropsWithChildren, ReactElement } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

type RouteRenderOptions = {
  path?: string;
  route?: string;
};

export function renderWithRouter(
  ui: ReactElement,
  { path = "/", route = "/" }: RouteRenderOptions = {},
  options?: Omit<RenderOptions, "wrapper">,
) {
  function Wrapper({ children }: PropsWithChildren) {
    return (
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={children} />
        </Routes>
      </MemoryRouter>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}
