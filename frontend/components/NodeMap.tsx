"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ReactFlow,
  Background,
  Controls,
  BackgroundVariant,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import MineNode from "@/components/MineNode";
import { computeRadialLayout, type Point } from "@/lib/mapLayout";
import { estimateStored } from "@/lib/mineProjection";
import { api, type MapEdgeOut, type MapNodeOut, type MineOut } from "@/lib/api";

export interface FlowNodeData extends MapNodeOut {
  mine: MineOut | null;
  now: number;
}

const nodeTypes = { mine: MineNode };
const ROOT_KEY = "start";
// Stable empty-array references so useMemo deps don't churn every render
// while the map/mines queries are loading/errored.
const EMPTY_NODES: MapNodeOut[] = [];
const EMPTY_EDGES: MapEdgeOut[] = [];
const EMPTY_MINES: MineOut[] = [];

function toFlowNodes(
  nodes: MapNodeOut[],
  layout: Record<string, Point>,
  minesById: Record<number, MineOut>,
  now: number,
): Node[] {
  return nodes.map((n) => ({
    id: n.node_key,
    type: "mine",
    position: layout[n.node_key] ?? { x: 0, y: 0 },
    data: { ...n, mine: n.mine_id ? (minesById[n.mine_id] ?? null) : null, now } satisfies FlowNodeData,
    draggable: false,
  }));
}

function toFlowEdges(edges: MapEdgeOut[], nodesByKey: Record<string, MapNodeOut>): Edge[] {
  return edges.map((e) => {
    // A path is "open" once its parent is unlocked (the child is then at
    // least discovered).
    const open = nodesByKey[e.source]?.status === "unlocked" && nodesByKey[e.target]?.status !== "locked";
    return {
      id: `${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      type: "straight",
      style: open
        ? { stroke: "#e0a339", strokeWidth: 2 }
        : { stroke: "#2a2f38", strokeWidth: 1.5, strokeDasharray: "4 4" },
    };
  });
}

function neighborsOf(nodeKey: string, edges: MapEdgeOut[]): string[] {
  return edges
    .filter((e) => e.source === nodeKey || e.target === nodeKey)
    .map((e) => (e.source === nodeKey ? e.target : e.source));
}

export default function NodeMap() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["map"], queryFn: api.getMap });
  const { data: mines } = useQuery({ queryKey: ["mines"], queryFn: api.getMines });
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Drives the live "pending amount" projection shown on mine nodes between
  // collects - purely cosmetic, doesn't touch the server.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const unlockMutation = useMutation({
    mutationFn: (nodeKey: string) => api.unlockNode(nodeKey),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["map"] }),
  });

  const collectMutation = useMutation({
    mutationFn: (mineId: number) => api.collectMine(mineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mines"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });

  const nodes = data?.nodes ?? EMPTY_NODES;
  const edges = data?.edges ?? EMPTY_EDGES;
  const minesList = mines ?? EMPTY_MINES;

  const nodesByKey = useMemo(() => Object.fromEntries(nodes.map((n) => [n.node_key, n])), [nodes]);
  const minesById = useMemo(() => Object.fromEntries(minesList.map((m) => [m.id, m])), [minesList]);
  const layout = useMemo(() => computeRadialLayout(edges, ROOT_KEY), [edges]);
  const flowNodes = useMemo(
    () => toFlowNodes(nodes, layout, minesById, now),
    [nodes, layout, minesById, now],
  );
  const flowEdges = useMemo(() => toFlowEdges(edges, nodesByKey), [edges, nodesByKey]);

  const handleNodeMouseEnter = useCallback<NodeMouseHandler>((_event, node) => {
    setHoveredId(node.id);
  }, []);

  const handleNodeClick = useCallback<NodeMouseHandler>(
    (_event, node) => {
      const target = nodesByKey[node.id];
      if (!target) return;
      if (target.status === "discovered") {
        unlockMutation.mutate(node.id);
      } else if (target.status === "unlocked" && target.mine_id) {
        collectMutation.mutate(target.mine_id);
      }
    },
    [nodesByKey, unlockMutation, collectMutation],
  );

  const hovered = hoveredId ? nodesByKey[hoveredId] : null;
  const hoveredMine = hovered?.mine_id ? minesById[hovered.mine_id] : null;
  const labelFor = useCallback(
    (key: string) => nodesByKey[key]?.resource?.name ?? "Home Base",
    [nodesByKey],
  );

  if (isLoading) {
    return <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading map…</div>;
  }

  if (isError || !data) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-red-400">
        Failed to load the map. Try refreshing.
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onNodeMouseEnter={handleNodeMouseEnter}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#242830" />
        <Controls showInteractive={false} />
      </ReactFlow>

      <div className="pointer-events-none absolute left-4 top-4 flex gap-3 rounded-lg border border-forge-border bg-forge-panel/90 px-3 py-2 text-xs text-slate-300">
        <LegendDot className="bg-forge-accent" label="Unlocked" />
        <LegendDot className="bg-slate-400" label="Discovered" />
        <LegendDot className="bg-slate-700" label="Locked" />
        <LegendDot className="bg-forge-rare" label="Rare" />
      </div>

      {hovered && (
        <div className="pointer-events-none absolute right-4 top-4 w-64 rounded-lg border border-forge-border bg-forge-panel/95 p-4 text-sm shadow-xl">
          <h3 className="font-medium text-slate-100">{hovered.resource ? hovered.resource.name : "Home Base"}</h3>
          <dl className="mt-3 space-y-1 text-slate-400">
            <div className="flex justify-between">
              <dt>Status</dt>
              <dd className="capitalize text-slate-200">{hovered.status}</dd>
            </div>
            {hovered.resource && (
              <div className="flex justify-between">
                <dt>Yield</dt>
                <dd className="text-forge-accent">{hovered.resource.yield_amount}/cycle</dd>
              </div>
            )}
            {hoveredMine && (
              <>
                <div className="flex justify-between">
                  <dt>Level</dt>
                  <dd className="text-slate-200">{hoveredMine.level}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Stored</dt>
                  <dd className="text-slate-200">
                    {estimateStored(hoveredMine, now)} / {hoveredMine.storage_capacity}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt>Cycle</dt>
                  <dd className="text-slate-200">{hoveredMine.cycle_seconds}s</dd>
                </div>
                <p className="pt-1 text-[11px] text-slate-500">Click the node to collect</p>
              </>
            )}
            <div className="flex justify-between gap-2">
              <dt className="shrink-0">Connects to</dt>
              <dd className="text-right text-slate-200">
                {neighborsOf(hovered.node_key, edges).map(labelFor).join(", ")}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

function LegendDot({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${className}`} />
      {label}
    </span>
  );
}
