import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

import { useMemo, useState } from "react";


function ArchitectureNode({ data }) {
  const confidence =
    data.confidence !== undefined &&
    data.confidence !== null
      ? `${Math.round(data.confidence * 100)}%`
      : "—";

  return (
    <div
      style={{
        width: "210px",
        padding: "16px 18px",
        borderRadius: "14px",

        background: data.selected
          ? "#17233b"
          : "#111a2b",

        border: data.selected
          ? "2px solid #6f8cff"
          : "1px solid #2b3953",

        boxShadow: data.selected
          ? "0 0 0 4px rgba(111,140,255,0.12)"
          : "0 8px 24px rgba(0,0,0,0.25)",

        color: "#f4f7ff",

        transition:
          "all 0.2s ease",

        cursor: "pointer",
      }}
    >

      <Handle
        type="target"
        position={Position.Left}
        style={{
          width: 9,
          height: 9,
          background: "#7893ff",
          border: "2px solid #111a2b",
        }}
      />


      <div
        style={{
          fontSize: "15px",
          fontWeight: 700,
          color: "#f6f8ff",
          marginBottom: "7px",
        }}
      >
        {data.label}
      </div>


      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
        }}
      >

        <span
          style={{
            padding: "4px 8px",
            borderRadius: "999px",
            background:
              "rgba(111,140,255,0.12)",
            color: "#aebcff",
            fontSize: "11px",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          {data.type || "unknown"}
        </span>


        <span
          style={{
            color: "#8492aa",
            fontSize: "11px",
          }}
        >
          {confidence}
        </span>

      </div>


      <Handle
        type="source"
        position={Position.Right}
        style={{
          width: 9,
          height: 9,
          background: "#7893ff",
          border: "2px solid #111a2b",
        }}
      />

    </div>
  );
}


const nodeTypes = {
  architectureNode:
    ArchitectureNode,
};


function buildLayout(
  entities = [],
  connections = [],
) {

  const incoming = {};

  entities.forEach((entity) => {
    incoming[
      entity.canonical_name
    ] = 0;
  });


  connections.forEach(
    ([source, target]) => {

      if (
        incoming[target] !==
        undefined
      ) {
        incoming[target] += 1;
      }

    }
  );


  const roots = entities.filter(
    (entity) =>
      (
        incoming[
          entity.canonical_name
        ] || 0
      ) === 0
  );


  const depth = {};

  roots.forEach((root) => {
    depth[
      root.canonical_name
    ] = 0;
  });


  let changed = true;
  let safety = 0;

  while (
    changed &&
    safety < 30
  ) {

    changed = false;
    safety += 1;


    connections.forEach(
      ([source, target]) => {

        if (
          depth[source] !==
          undefined
        ) {

          const nextDepth =
            depth[source] + 1;


          if (
            depth[target] ===
              undefined ||
            nextDepth >
              depth[target]
          ) {

            depth[target] =
              nextDepth;

            changed = true;
          }

        }

      }
    );
  }


  entities.forEach((entity) => {

    if (
      depth[
        entity.canonical_name
      ] === undefined
    ) {

      depth[
        entity.canonical_name
      ] = 0;

    }

  });


  const levels = {};

  entities.forEach((entity) => {

    const level =
      depth[
        entity.canonical_name
      ] || 0;

    if (!levels[level]) {
      levels[level] = [];
    }

    levels[level].push(entity);

  });


  const nodes = [];


  Object.keys(levels)
    .map(Number)
    .sort((a, b) => a - b)
    .forEach((level) => {

      const levelEntities =
        levels[level];

      const totalHeight =
        (
          levelEntities.length - 1
        ) * 160;


      levelEntities.forEach(
        (entity, index) => {

          nodes.push({
            id:
              entity.entity_id ||
              entity.canonical_name,

            type:
              "architectureNode",

            position: {
              x: level * 310,

              y:
                index * 160 -
                totalHeight / 2,
            },

            data: {
              label:
                entity.canonical_name,

              type:
                entity.type,

              confidence:
                entity.confidence,

              entity,
            },
          });

        }
      );

    });


  const nameToId = {};

  entities.forEach((entity) => {

    nameToId[
      entity.canonical_name
    ] =
      entity.entity_id ||
      entity.canonical_name;

  });


  const edges =
    connections
      .filter(
        ([source, target]) =>
          nameToId[source] &&
          nameToId[target]
      )
      .map(
        (
          [source, target],
          index
        ) => ({
          id:
            `edge-${index}-${source}-${target}`,

          source:
            nameToId[source],

          target:
            nameToId[target],

          markerEnd: {
            type:
              MarkerType.ArrowClosed,

            color:
              "#7184a8",
          },

          style: {
            stroke:
              "#5e7196",

            strokeWidth: 2,
          },
        })
      );


  return {
    nodes,
    edges,
  };
}


function DetailItem({
  label,
  children,
}) {
  return (
    <div
      style={{
        marginBottom: "20px",
      }}
    >

      <div
        style={{
          color: "#71809b",
          fontSize: "11px",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "8px",
        }}
      >
        {label}
      </div>

      <div
        style={{
          color: "#dbe3f3",
          fontSize: "13px",
          lineHeight: 1.6,
        }}
      >
        {children}
      </div>

    </div>
  );
}


function DetailsPanel({
  entity,
  onClose,
}) {

  if (!entity) {
    return null;
  }


  const confidence =
    entity.confidence !== undefined &&
    entity.confidence !== null
      ? `${Math.round(
          entity.confidence * 100
        )}%`
      : "Unknown";


  return (
    <aside
      style={{
        width: "340px",
        minWidth: "340px",
        height: "100%",
        overflowY: "auto",

        background:
          "#0c1423",

        borderLeft:
          "1px solid #27344d",

        padding: "24px",

        boxSizing:
          "border-box",
      }}
    >

      <div
        style={{
          display: "flex",
          justifyContent:
            "space-between",
          alignItems:
            "flex-start",
          gap: "12px",
          marginBottom: "24px",
        }}
      >

        <div>

          <div
            style={{
              color: "#788cff",
              fontSize: "11px",
              fontWeight: 700,
              letterSpacing:
                "0.08em",
              textTransform:
                "uppercase",
              marginBottom: "8px",
            }}
          >
            Component
          </div>

          <h3
            style={{
              color: "#f5f7ff",
              fontSize: "20px",
              margin: 0,
            }}
          >
            {
              entity.canonical_name
            }
          </h3>

          <div
            style={{
              color: "#8896af",
              fontSize: "13px",
              marginTop: "5px",
            }}
          >
            {entity.type}
          </div>

        </div>


        <button
          type="button"
          onClick={onClose}
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",

            border:
              "1px solid #28364f",

            background:
              "#141e30",

            color: "#aeb9ce",

            fontSize: "20px",

            cursor: "pointer",
          }}
        >
          ×
        </button>

      </div>


      <DetailItem label="Confidence">
        <strong
          style={{
            fontSize: "20px",
            color: "#f3f6ff",
          }}
        >
          {confidence}
        </strong>
      </DetailItem>


      <DetailItem label="Dependencies">

        {
          entity.dependencies?.length
            ? entity.dependencies.map(
                (item) => (
                  <div key={item}>
                    → {item}
                  </div>
                )
              )
            : (
              <span
                style={{
                  color: "#66758f",
                }}
              >
                None detected
              </span>
            )
        }

      </DetailItem>


      <DetailItem label="Dependents">

        {
          entity.dependents?.length
            ? entity.dependents.map(
                (item) => (
                  <div key={item}>
                    ← {item}
                  </div>
                )
              )
            : (
              <span
                style={{
                  color: "#66758f",
                }}
              >
                None detected
              </span>
            )
        }

      </DetailItem>


      <DetailItem label="Aliases">

        {
          entity.aliases?.length
            ? entity.aliases.join(", ")
            : "No aliases"
        }

      </DetailItem>


      <DetailItem label="Graph Metrics">

        <div>
          In-degree:{" "}
          <strong>
            {
              entity.in_degree
              ?? 0
            }
          </strong>
        </div>

        <div>
          Out-degree:{" "}
          <strong>
            {
              entity.out_degree
              ?? 0
            }
          </strong>
        </div>

      </DetailItem>


      <DetailItem label="Evidence">

        {
          entity.evidence?.length
            ? entity.evidence.map(
                (
                  evidence,
                  index
                ) => (

                  <div
                    key={index}
                    style={{
                      background:
                        "#111b2d",

                      border:
                        "1px solid #24324a",

                      borderRadius:
                        "10px",

                      padding:
                        "12px",

                      marginBottom:
                        "8px",
                    }}
                  >

                    <strong>
                      {
                        evidence.filename
                        ||
                        "Evidence"
                      }
                    </strong>

                    {
                      evidence.reason && (
                        <div
                          style={{
                            color:
                              "#8795ac",

                            marginTop:
                              "5px",

                            fontSize:
                              "12px",
                          }}
                        >
                          {
                            evidence.reason
                          }
                        </div>
                      )
                    }

                  </div>

                )
              )
            : (
              <span
                style={{
                  color: "#66758f",
                }}
              >
                No evidence available
              </span>
            )
        }

      </DetailItem>

    </aside>
  );
}


export default function ArchitectureGraph({
  digitalTwin,
}) {

  const [
    selectedEntity,
    setSelectedEntity,
  ] = useState(null);


  const graphData =
    useMemo(
      () =>
        buildLayout(
          digitalTwin?.entities ||
            [],

          digitalTwin?.connections ||
            []
        ),
      [digitalTwin]
    );


  const nodes =
    graphData.nodes.map(
      (node) => ({
        ...node,

        data: {
          ...node.data,

          selected:
            selectedEntity
              ?.canonical_name ===
            node.data.entity
              .canonical_name,
        },
      })
    );


  if (
    !digitalTwin ||
    !digitalTwin.entities?.length
  ) {

    return (
      <div
        style={{
          minHeight: "420px",

          display: "grid",
          placeItems: "center",

          border:
            "1px dashed #293650",

          borderRadius:
            "14px",

          background:
            "#0b1321",

          color:
            "#73819b",
        }}
      >
        No architecture graph available.
      </div>
    );
  }


  return (
    <div
      style={{
        display: "flex",

        height: "560px",

        overflow: "hidden",

        border:
          "1px solid #27344b",

        borderRadius:
          "16px",

        background:
          "#0b1321",

        marginTop:
          "18px",
      }}
    >

      <div
        style={{
          flex: 1,
          minWidth: 0,
        }}
      >

        <ReactFlow
          nodes={nodes}
          edges={graphData.edges}

          nodeTypes={
            nodeTypes
          }

          fitView

          fitViewOptions={{
            padding: 0.28,
            minZoom: 0.8,
            maxZoom: 1.05,
          }}

          minZoom={0.5}
          maxZoom={1.7}

          onNodeClick={(
            _event,
            node
          ) =>
            setSelectedEntity(
              node.data.entity
            )
          }

          proOptions={{
            hideAttribution: true,
          }}

          style={{
            background:
              "#0b1321",
          }}
        >

          <Background
            gap={26}
            size={1}
            color="#1e2a3d"
          />

          <MiniMap
            pannable
            zoomable
            nodeColor="#536995"
            maskColor="rgba(5, 10, 20, 0.65)"
            style={{
              background:
                "#111a29",

              border:
                "1px solid #26344b",

              borderRadius:
                "10px",
            }}
          />

          <Controls
            position="bottom-left"
            style={{
              borderRadius:
                "10px",

              overflow:
                "hidden",
            }}
          />

        </ReactFlow>

      </div>


      {selectedEntity && (

        <DetailsPanel
          entity={
            selectedEntity
          }

          onClose={() =>
            setSelectedEntity(
              null
            )
          }
        />

      )}

    </div>
  );
}