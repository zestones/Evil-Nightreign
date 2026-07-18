import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { heroArt } from "@/lib/api";

/* ---------- canvas-texture helpers (cold gothic backdrop, light, glow) ------ */
function gradientTex(draw: (x: CanvasRenderingContext2D, w: number, h: number) => void, w = 1024, h = 1024) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d")!, w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function useBackdropTex() {
  // near-black void with only a very dim cold glow high up
  return useMemo(
    () =>
      gradientTex((x, w, h) => {
        const g = x.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, "#090d16");
        g.addColorStop(0.5, "#06080f");
        g.addColorStop(1, "#05070c");
        x.fillStyle = g;
        x.fillRect(0, 0, w, h);
        const rg = x.createRadialGradient(w / 2, h * 0.2, 20, w / 2, h * 0.2, w * 0.5);
        rg.addColorStop(0, "rgba(58,82,138,0.16)");
        rg.addColorStop(1, "rgba(58,82,138,0)");
        x.fillStyle = rg;
        x.fillRect(0, 0, w, h);
      }),
    []
  );
}

function useArchTex() {
  // crisp thin-line lancet gothic arch (outer + inner keyline + apex trefoil)
  return useMemo(
    () =>
      gradientTex((x, w, h) => {
        x.clearRect(0, 0, w, h);
        const cx = w / 2;
        const lancet = (inset: number, springY: number, apexY: number) => {
          x.beginPath();
          x.moveTo(inset, h);
          x.lineTo(inset, springY);
          x.quadraticCurveTo(inset, apexY + (springY - apexY) * 0.32, cx, apexY);
          x.quadraticCurveTo(w - inset, apexY + (springY - apexY) * 0.32, w - inset, springY);
          x.lineTo(w - inset, h);
          x.stroke();
        };
        x.strokeStyle = "rgba(178,194,216,0.5)";
        x.lineWidth = 3;
        lancet(w * 0.1, h * 0.46, h * 0.07);
        x.strokeStyle = "rgba(178,194,216,0.2)";
        x.lineWidth = 1.5;
        lancet(w * 0.145, h * 0.44, h * 0.115);
        // apex trefoil
        x.strokeStyle = "rgba(178,194,216,0.4)";
        x.lineWidth = 2;
        x.beginPath();
        x.arc(cx, h * 0.17, w * 0.016, 0, 6.2832);
        x.stroke();
        x.beginPath();
        x.arc(cx - w * 0.026, h * 0.2, w * 0.012, 0, 6.2832);
        x.stroke();
        x.beginPath();
        x.arc(cx + w * 0.026, h * 0.2, w * 0.012, 0, 6.2832);
        x.stroke();
      }, 1024, 1024),
    []
  );
}

function useRadialTex(color: string) {
  return useMemo(
    () =>
      gradientTex((x, w, h) => {
        const g = x.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
        g.addColorStop(0, color);
        g.addColorStop(1, "rgba(0,0,0,0)");
        x.fillStyle = g;
        x.fillRect(0, 0, w, h);
      }, 512, 512),
    [color]
  );
}

function useSpriteTex() {
  return useMemo(
    () =>
      gradientTex((x, w, h) => {
        const g = x.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
        g.addColorStop(0, "rgba(255,255,255,1)");
        g.addColorStop(0.35, "rgba(255,255,255,0.7)");
        g.addColorStop(1, "rgba(255,255,255,0)");
        x.fillStyle = g;
        x.fillRect(0, 0, w, h);
      }, 64, 64),
    []
  );
}

/* ---------- the hero billboard (full, uncropped) ---------------------------
   Two overlapping layers cross-fade: the incoming portrait fades IN while the
   outgoing one fades OUT at the same time, so the stage is never empty. The old
   code faded fully to 0, THEN loaded and faded back up — that produced the
   "blink" to an empty arch on every character switch. */
type Layer = { tex: THREE.Texture; aspect: number };
function Hero({ name, groundY, targetH }: { name: string; groundY: number; targetH: number }) {
  const matA = useRef<THREE.MeshBasicMaterial>(null!);
  const matB = useRef<THREE.MeshBasicMaterial>(null!);
  const [slotA, setSlotA] = useState<Layer | null>(null);
  const [slotB, setSlotB] = useState<Layer | null>(null);
  const opA = useRef(0);
  const opB = useRef(0);
  const tgtA = useRef(0);
  const tgtB = useRef(0);
  const incoming = useRef<"A" | "B">("A"); // which slot the next portrait lands in

  useEffect(() => {
    let alive = true;
    const loader = new THREE.TextureLoader();
    loader.load(
      heroArt(name),
      (t) => {
        if (!alive) return;
        t.colorSpace = THREE.SRGBColorSpace;
        t.anisotropy = 8;
        t.minFilter = THREE.LinearMipmapLinearFilter;
        t.magFilter = THREE.LinearFilter;
        const img = t.image as HTMLImageElement;
        const layer = { tex: t, aspect: img.width / img.height };
        // new portrait enters the free slot and fades up; the other fades out
        if (incoming.current === "A") {
          setSlotA(layer);
          opA.current = 0;
          tgtA.current = 1;
          tgtB.current = 0;
          incoming.current = "B";
        } else {
          setSlotB(layer);
          opB.current = 0;
          tgtB.current = 1;
          tgtA.current = 0;
          incoming.current = "A";
        }
      },
      undefined,
      () => {
        // no portrait for this character (e.g. Scholar/Undertaker): fade both out
        if (!alive) return;
        tgtA.current = 0;
        tgtB.current = 0;
      }
    );
    return () => {
      alive = false;
    };
  }, [name]);

  useFrame((_, dt) => {
    const d = Math.min(dt, 0.05) * 6;
    opA.current += (tgtA.current - opA.current) * d;
    opB.current += (tgtB.current - opB.current) * d;
    if (matA.current) matA.current.opacity = Math.max(0, opA.current);
    if (matB.current) matB.current.opacity = Math.max(0, opB.current);
  });

  const plane = (slot: Layer | null, matRef: React.RefObject<THREE.MeshBasicMaterial>, z: number) => {
    if (!slot) return null;
    const h = targetH;
    const w = h * slot.aspect;
    return (
      <mesh position={[0, groundY + h / 2, z]}>
        <planeGeometry args={[w, h]} />
        <meshBasicMaterial ref={matRef} map={slot.tex} transparent opacity={0} toneMapped={false} depthWrite={false} />
      </mesh>
    );
  };

  return (
    <>
      {plane(slotA, matA, 0.2)}
      {plane(slotB, matB, 0.21)}
    </>
  );
}

/* ---------- drifting motes (two depth layers) ------------------------------- */
function Motes({ count, zBase, zSpread, size, warm, sprite }: { count: number; zBase: number; zSpread: number; size: number; warm: number; sprite: THREE.Texture }) {
  const ref = useRef<THREE.Points>(null!);
  const { positions, colors, speeds } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const speeds = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 14;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 2] = zBase + Math.random() * zSpread;
      speeds[i] = 0.05 + Math.random() * 0.18;
      const c = new THREE.Color();
      if (Math.random() < warm) c.set("#e8cf8a");
      else c.setHSL(0.58, 0.35, 0.55 + Math.random() * 0.22);
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    return { positions, colors, speeds };
  }, [count, zBase, zSpread, warm]);

  useFrame((_, dt) => {
    const attr = ref.current.geometry.attributes.position as THREE.BufferAttribute;
    const a = attr.array as Float32Array;
    const d = Math.min(dt, 0.05);
    for (let i = 0; i < count; i++) {
      a[i * 3 + 1] += speeds[i] * d;
      a[i * 3] += Math.sin((a[i * 3 + 1] + i) * 0.3) * d * 0.05;
      if (a[i * 3 + 1] > 5.5) {
        a[i * 3 + 1] = -5.5;
        a[i * 3] = (Math.random() - 0.5) * 14;
      }
    }
    attr.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial map={sprite} size={size} vertexColors transparent opacity={0.8} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
    </points>
  );
}

/* ---------- scene contents (with pointer parallax) -------------------------- */
function SceneContents({ name }: { name: string }) {
  const group = useRef<THREE.Group>(null!);
  const { viewport } = useThree();
  const backdrop = useBackdropTex();
  const arch = useArchTex();
  const glow = useRadialTex("rgba(110,140,195,0.5)");
  const sprite = useSpriteTex();

  // world height visible at z=0 → size the hero so the WHOLE figure is in view,
  // feet ~10% above the bottom edge (never cropped)
  const worldH = viewport.height;
  const groundY = -worldH / 2 + worldH * 0.1;
  const heroH = worldH * 0.82;

  return (
    <group ref={group}>
      {/* backdrop */}
      <mesh position={[0, 0, -6]}>
        <planeGeometry args={[viewport.width * 1.6 + 6, viewport.height * 1.6 + 6]} />
        <meshBasicMaterial map={backdrop} depthWrite={false} toneMapped={false} />
      </mesh>
      {/* dim apex glow (light from the top of the arch) */}
      <mesh position={[0, groundY + heroH * 0.82, -3]}>
        <planeGeometry args={[heroH * 0.85, heroH * 0.85]} />
        <meshBasicMaterial map={glow} transparent depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} opacity={0.4} />
      </mesh>
      {/* crisp thin-line gothic arch framing the hero */}
      <mesh position={[0, groundY + heroH * 0.5, -2.5]}>
        <planeGeometry args={[heroH * 0.98, heroH * 1.32]} />
        <meshBasicMaterial map={arch} transparent depthWrite={false} toneMapped={false} opacity={0.85} />
      </mesh>
      {/* far motes */}
      <Motes count={200} zBase={-4} zSpread={2.5} size={0.06} warm={0.1} sprite={sprite} />
      {/* the hero */}
      <Hero name={name} groundY={groundY} targetH={heroH} />
      {/* subtle ground stage glow at the feet */}
      <mesh position={[0, groundY + worldH * 0.02, 0.4]}>
        <planeGeometry args={[heroH * 0.9, worldH * 0.14]} />
        <meshBasicMaterial map={glow} transparent depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} opacity={0.4} />
      </mesh>
      {/* near motes (drift in front for depth) */}
      <Motes count={90} zBase={2} zSpread={2} size={0.13} warm={0.14} sprite={sprite} />
    </group>
  );
}

export function Scene({ name }: { name: string }) {
  return (
    <div className="fixed inset-0 -z-0">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 42 }}
        dpr={[1, 1.9]}
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
      >
        <color attach="background" args={["#05070c"]} />
        <fog attach="fog" args={["#05070c", 9, 22]} />
        <SceneContents name={name} />
      </Canvas>
      {/* vignette + floor darkening on top of the canvas */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 100% at 50% 42%, transparent 46%, rgba(0,0,0,0.55) 100%)," +
            "linear-gradient(0deg, rgba(5,7,12,0.85) 0%, transparent 26%)",
        }}
      />
    </div>
  );
}
