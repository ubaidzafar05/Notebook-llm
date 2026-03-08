import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createNotebook, updateNotebook } from "../lib/api";
import { queryClient } from "../app/queryClient";
import type { Notebook } from "../types/api";
import styles from "./Workspace.module.css";

type NotebookRailProps = {
  notebookId: string;
  currentNotebook: Notebook | undefined;
  notebooks: Notebook[];
};

export function NotebookRail(props: NotebookRailProps): JSX.Element {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [editTitle, setEditTitle] = useState(props.currentNotebook?.title ?? "");
  const [editDescription, setEditDescription] = useState(props.currentNotebook?.description ?? "");

  useEffect(() => {
    setEditTitle(props.currentNotebook?.title ?? "");
    setEditDescription(props.currentNotebook?.description ?? "");
  }, [props.currentNotebook?.description, props.currentNotebook?.title]);

  const createMutation = useMutation({
    mutationFn: () => createNotebook(title.trim(), description.trim()),
    onSuccess: (notebook) => {
      setTitle("");
      setDescription("");
      void queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      navigate(`/notebooks/${notebook.id}`);
    },
  });
  const updateMutation = useMutation({
    mutationFn: () => updateNotebook(props.notebookId, editTitle.trim(), editDescription.trim()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notebooks"] });
    },
  });

  return (
    <div className={styles.column}>
      <div className={styles.panelHeader}>
        <p className={styles.eyebrow}>Notebooks</p>
        <h2 className={styles.panelTitle}>Workspace Rail</h2>
      </div>
      <div className={styles.panelBody}>
        <section className={styles.section}>
          <div className={styles.cardList}>
            {props.notebooks.map((notebook) => (
              <button
                key={notebook.id}
                className={notebook.id === props.notebookId ? styles.cardActive : styles.card}
                onClick={() => navigate(`/notebooks/${notebook.id}`)}
                type="button"
              >
                <p className={styles.cardTitle}>{notebook.title}</p>
                <p className={styles.cardMeta}>{notebook.description ?? "Notebook-scoped source and session memory"}</p>
              </button>
            ))}
          </div>
        </section>
        <section className={styles.section}>
          <p className={styles.eyebrow}>Create Notebook</p>
          <label className={styles.label}>
            Title
            <input className={styles.input} value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className={styles.label}>
            Description
            <textarea className={styles.textarea} value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <button className={styles.button} disabled={!title.trim() || createMutation.isPending} onClick={() => createMutation.mutate()} type="button">
            {createMutation.isPending ? "Creating..." : "Create Notebook"}
          </button>
        </section>
        <section className={styles.section}>
          <p className={styles.eyebrow}>Notebook Details</p>
          <label className={styles.label}>
            Title
            <input className={styles.input} value={editTitle} onChange={(event) => setEditTitle(event.target.value)} />
          </label>
          <label className={styles.label}>
            Description
            <textarea className={styles.textarea} value={editDescription} onChange={(event) => setEditDescription(event.target.value)} />
          </label>
          <button
            className={styles.secondaryButton}
            disabled={!editTitle.trim() || updateMutation.isPending}
            onClick={() => updateMutation.mutate()}
            type="button"
          >
            {updateMutation.isPending ? "Saving..." : "Save Notebook"}
          </button>
        </section>
      </div>
    </div>
  );
}
