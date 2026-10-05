import "leaflet/dist/leaflet.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { HashScroll } from "./components/HashScroll";
import { LandingPage } from "./pages/LandingPage";
import { PlannerPage } from "./pages/PlannerPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import "./index.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <HashScroll />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/plan" element={<PlannerPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
