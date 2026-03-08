import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { listNotebooks } from "../lib/api";
import { NotebookRail } from "../components/NotebookRail";
import { SourcePanel } from "../components/SourcePanel";
import { ChatPanel } from "../components/ChatPanel";
import { StudioPanel } from "../components/StudioPanel";
import { useWorkspaceStore } from "../state/workspace-store";
import styles from "../components/Workspace.module.css";

export function NotebookPage(): JSX.Element {
  const params = useParams();
  const notebookId = params.notebookId ?? "";
  const setNotebookContext = useWorkspaceStore((state) => state.setNotebookContext);
  const notebooksQuery = useQuery({
    queryKey: ["notebooks"],
    queryFn: listNotebooks,
  });

  useEffect(() => {
    if (notebookId) {
      setNotebookContext(notebookId);
    }
  }, [notebookId, setNotebookContext]);

  const currentNotebook = notebooksQuery.data?.find((item) => item.id === notebookId);
  if (!notebookId || notebooksQuery.isLoading) {
    return <div className="app-loader">Loading notebook...</div>;
  }
  return (
    <div className={styles.layout}>
      <div className={styles.stack}>
        <NotebookRail currentNotebook={currentNotebook} notebookId={notebookId} notebooks={notebooksQuery.data ?? []} />
        <SourcePanel notebookId={notebookId} />
      </div>
      <ChatPanel notebookId={notebookId} />
      <StudioPanel notebookId={notebookId} />
    </div>
  );
}
