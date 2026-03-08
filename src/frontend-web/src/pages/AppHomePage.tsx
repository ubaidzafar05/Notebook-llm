import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { listNotebooks } from "../lib/api";

export function AppHomePage(): JSX.Element {
  const { data, isLoading } = useQuery({
    queryKey: ["notebooks"],
    queryFn: listNotebooks,
  });
  if (isLoading) {
    return <div className="app-loader">Loading notebooks...</div>;
  }
  const notebook = data?.[0];
  if (!notebook) {
    return <div className="app-loader">No notebook found for this account.</div>;
  }
  return <Navigate to={`/notebooks/${notebook.id}`} replace />;
}
