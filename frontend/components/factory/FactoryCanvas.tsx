"use client";

import { useCallback, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ReactFlow,
  Background,
  Controls,
  BackgroundVariant,
  type Edge,
  type Node,
  type OnConnect,
  type OnEdgesDelete,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import MachineNode, { type MachineNodeData } from "@/components/factory/MachineNode";
import EmptyCellNode, { type EmptyCellNodeData } from "@/components/factory/EmptyCellNode";
import { api, ApiError, type FactoryGridOut } from "@/lib/api";

const nodeTypes = { machine: MachineNode, empty: EmptyCellNode };
const CELL_SIZE = 150;

function machineNodeId(machineId: number) {
  return `machine-${machineId}`;
}

function machineIdFromNodeId(nodeId: string) {
  return Number(nodeId.replace("machine-", ""));
}

export default function FactoryCanvas({
  grid,
  armedKey,
  onArmedConsumed,
}: {
  grid: FactoryGridOut;
  armedKey: string | null;
  onArmedConsumed: () => void;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["factory-grids"] });
  const reportError = (err: unknown, fallback: string) =>
    setError(err instanceof ApiError ? err.message : fallback);

  const placeMutation = useMutation({
    mutationFn: (vars: { x: number; y: number }) => api.placeMachine(grid.id, armedKey as string, vars.x, vars.y),
    onSuccess: () => {
      invalidate();
      onArmedConsumed();
    },
    onError: (err) => reportError(err, "Couldn't place machine"),
  });

  const removeMutation = useMutation({
    mutationFn: (machineId: number) => api.removeMachine(machineId),
    onSuccess: invalidate,
  });

  const connectMutation = useMutation({
    mutationFn: (vars: { source: number; target: number }) => api.connectMachines(vars.source, vars.target),
    onSuccess: invalidate,
    onError: (err) => reportError(err, "Couldn't connect machines"),
  });

  const disconnectMutation = useMutation({
    mutationFn: (connectionId: number) => api.disconnectMachines(connectionId),
    onSuccess: invalidate,
  });

  const flowNodes: Node[] = useMemo(() => {
    const machineByCell = new Map(grid.machines.map((m) => [`${m.x},${m.y}`, m]));
    const nodes: Node[] = [];

    for (let y = 0; y < grid.height; y++) {
      for (let x = 0; x < grid.width; x++) {
        const machine = machineByCell.get(`${x},${y}`);
        if (machine) {
          nodes.push({
            id: machineNodeId(machine.id),
            type: "machine",
            position: { x: x * CELL_SIZE, y: y * CELL_SIZE },
            data: { ...machine, onDelete: (id: number) => removeMutation.mutate(id) } satisfies MachineNodeData,
            draggable: false,
          });
        } else {
          nodes.push({
            id: `empty-${x}-${y}`,
            type: "empty",
            position: { x: x * CELL_SIZE, y: y * CELL_SIZE },
            data: {
              x,
              y,
              armed: !!armedKey,
              onPlace: (px: number, py: number) => placeMutation.mutate({ x: px, y: py }),
            } satisfies EmptyCellNodeData,
            draggable: false,
            selectable: false,
          });
        }
      }
    }
    return nodes;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grid, armedKey]);

  const flowEdges: Edge[] = useMemo(
    () =>
      grid.connections.map((c) => ({
        id: `connection-${c.id}`,
        source: machineNodeId(c.source_machine_id),
        target: machineNodeId(c.target_machine_id),
        data: { connectionId: c.id },
        type: "straight",
        style: { stroke: "#e0a339", strokeWidth: 2 },
      })),
    [grid.connections],
  );

  const handleConnect = useCallback<OnConnect>(
    (params) => {
      if (!params.source || !params.target) return;
      connectMutation.mutate({
        source: machineIdFromNodeId(params.source),
        target: machineIdFromNodeId(params.target),
      });
    },
    [connectMutation],
  );

  const handleEdgesDelete = useCallback<OnEdgesDelete>(
    (edges) => {
      for (const edge of edges) {
        const connectionId = (edge.data as { connectionId?: number } | undefined)?.connectionId;
        if (connectionId) disconnectMutation.mutate(connectionId);
      }
    },
    [disconnectMutation],
  );

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onConnect={handleConnect}
        onEdgesDelete={handleEdgesDelete}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#242830" />
        <Controls showInteractive={false} />
      </ReactFlow>

      {error && (
        <div className="absolute left-1/2 top-4 -translate-x-1/2 rounded-md border border-red-500/40 bg-forge-panel px-3 py-1.5 text-xs text-red-400 shadow-lg">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-100">
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
