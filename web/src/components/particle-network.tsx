"use client"

import { useRef, useMemo } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import * as THREE from "three"

const NODE_COUNT = 50
const CONNECTION_DISTANCE = 2.8
const BOUNDS = 8

interface Node {
  position: THREE.Vector3
  velocity: THREE.Vector3
  blocked: boolean
}

function NetworkScene() {
  const nodesRef = useRef<Node[]>([])
  const pointsRef = useRef<THREE.Points>(null)
  const linesRef = useRef<THREE.LineSegments>(null)
  const blockedTimers = useRef<number[]>(new Array(NODE_COUNT).fill(0))

  useMemo(() => {
    const arr: Node[] = []
    for (let i = 0; i < NODE_COUNT; i++) {
      arr.push({
        position: new THREE.Vector3(
          (Math.random() - 0.5) * BOUNDS * 2,
          (Math.random() - 0.5) * BOUNDS * 2,
          (Math.random() - 0.5) * BOUNDS * 0.5
        ),
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 0.006,
          (Math.random() - 0.5) * 0.006,
          (Math.random() - 0.5) * 0.002
        ),
        blocked: i % 7 === 0,
      })
    }
    nodesRef.current = arr
    return arr
  }, [])

  const pointPositions = useMemo(() => new Float32Array(NODE_COUNT * 3), [])
  const pointColors = useMemo(() => new Float32Array(NODE_COUNT * 3), [])
  const linePositions = useMemo(() => new Float32Array(NODE_COUNT * NODE_COUNT * 6), [])
  const lineColors = useMemo(() => new Float32Array(NODE_COUNT * NODE_COUNT * 6), [])

  const accentColor = useMemo(() => new THREE.Color("#FF3B30"), [])
  const nodeColor = useMemo(() => new THREE.Color("#FF6B6B"), [])
  const lineColor = useMemo(() => new THREE.Color("#FF3B30"), [])

  useFrame((_, delta) => {
    const pts = nodesRef.current
    let lineIdx = 0

    for (let i = 0; i < pts.length; i++) {
      const node = pts[i]
      node.position.add(node.velocity)

      if (Math.abs(node.position.x) > BOUNDS) node.velocity.x *= -1
      if (Math.abs(node.position.y) > BOUNDS) node.velocity.y *= -1
      if (Math.abs(node.position.z) > BOUNDS * 0.25) node.velocity.z *= -1

      pointPositions[i * 3] = node.position.x
      pointPositions[i * 3 + 1] = node.position.y
      pointPositions[i * 3 + 2] = node.position.z

      if (node.blocked) {
        blockedTimers.current[i] += delta * 2
        const pulse = Math.sin(blockedTimers.current[i]) * 0.5 + 0.5
        pointColors[i * 3] = accentColor.r * (0.4 + pulse * 0.6)
        pointColors[i * 3 + 1] = accentColor.g * pulse * 0.2
        pointColors[i * 3 + 2] = accentColor.b * pulse * 0.2
      } else {
        pointColors[i * 3] = nodeColor.r * 0.5
        pointColors[i * 3 + 1] = nodeColor.g * 0.3
        pointColors[i * 3 + 2] = nodeColor.b * 0.3
      }
    }

    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const dist = pts[i].position.distanceTo(pts[j].position)
        if (dist < CONNECTION_DISTANCE) {
          const opacity = 1 - dist / CONNECTION_DISTANCE

          linePositions[lineIdx * 6] = pts[i].position.x
          linePositions[lineIdx * 6 + 1] = pts[i].position.y
          linePositions[lineIdx * 6 + 2] = pts[i].position.z
          linePositions[lineIdx * 6 + 3] = pts[j].position.x
          linePositions[lineIdx * 6 + 4] = pts[j].position.y
          linePositions[lineIdx * 6 + 5] = pts[j].position.z

          const isBlocked = pts[i].blocked || pts[j].blocked
          const col = isBlocked ? accentColor : lineColor

          lineColors[lineIdx * 6] = col.r * opacity * 0.3
          lineColors[lineIdx * 6 + 1] = col.g * opacity * 0.3
          lineColors[lineIdx * 6 + 2] = col.b * opacity * 0.3
          lineColors[lineIdx * 6 + 3] = col.r * opacity * 0.3
          lineColors[lineIdx * 6 + 4] = col.g * opacity * 0.3
          lineColors[lineIdx * 6 + 5] = col.b * opacity * 0.3

          lineIdx++
        }
      }
    }

    for (let k = lineIdx * 6; k < linePositions.length; k++) {
      linePositions[k] = 0
      lineColors[k] = 0
    }

    if (pointsRef.current) {
      pointsRef.current.geometry.attributes.position.needsUpdate = true
      pointsRef.current.geometry.attributes.color.needsUpdate = true
    }
    if (linesRef.current) {
      linesRef.current.geometry.attributes.position.needsUpdate = true
      linesRef.current.geometry.attributes.color.needsUpdate = true
    }
  })

  return (
    <>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[pointPositions, 3]}
            count={NODE_COUNT}
          />
          <bufferAttribute
            attach="attributes-color"
            args={[pointColors, 3]}
            count={NODE_COUNT}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.05}
          vertexColors
          transparent
          opacity={0.7}
          sizeAttenuation
          depthWrite={false}
        />
      </points>

      <lineSegments ref={linesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[linePositions, 3]}
            count={NODE_COUNT * NODE_COUNT}
          />
          <bufferAttribute
            attach="attributes-color"
            args={[lineColors, 3]}
            count={NODE_COUNT * NODE_COUNT}
          />
        </bufferGeometry>
        <lineBasicMaterial vertexColors transparent opacity={0.5} depthWrite={false} />
      </lineSegments>
    </>
  )
}

export function ParticleNetwork() {
  return (
    <div className="absolute inset-0 z-0">
      <Canvas
        camera={{ position: [0, 0, 8], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 1.5]}
        style={{ background: "transparent" }}
      >
        <NetworkScene />
      </Canvas>
    </div>
  )
}
