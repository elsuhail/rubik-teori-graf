import { useRef, useState, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useRubikStore, type RotationCommand } from '../../store/useRubikStore';

// Define the colors for the faces
const faceColors = {
  right: '#ef4444', // red
  left: '#f97316', // orange
  up: '#eab308', // yellow
  down: '#ffffff', // white
  front: '#22c55e', // green
  back: '#3b82f6', // blue
  black: '#1e293b' // core/border
};

// Generate initial 27 cubies positions and colors
const generateInitialCubies = () => {
  const cubies = [];
  for (let x = -1; x <= 1; x++) {
    for (let y = -1; y <= 1; y++) {
      for (let z = -1; z <= 1; z++) {
        // Color mapping based on position
        const colors = [
          x === 1 ? faceColors.right : faceColors.black,
          x === -1 ? faceColors.left : faceColors.black,
          y === 1 ? faceColors.up : faceColors.black,
          y === -1 ? faceColors.down : faceColors.black,
          z === 1 ? faceColors.front : faceColors.black,
          z === -1 ? faceColors.back : faceColors.black,
        ];
        
        cubies.push({
          id: `${x}_${y}_${z}`,
          position: new THREE.Vector3(x, y, z),
          rotation: new THREE.Euler(0, 0, 0),
          colors,
          matrix: new THREE.Matrix4().makeTranslation(x, y, z)
        });
      }
    }
  }
  return cubies;
};

const Cubie = ({ data }: any) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  useEffect(() => {
    // Note: in StrictMode this runs twice, but setting matrix elements directly is safe
    if (meshRef.current) {
      meshRef.current.matrixAutoUpdate = false;
      meshRef.current.matrix.copy(data.matrix);
    }
  }, [data.matrix]);

  return (
    <mesh ref={meshRef}>
      <boxGeometry args={[0.95, 0.95, 0.95]} />
      {data.colors.map((color: string, index: number) => (
        <meshStandardMaterial key={index} attach={`material-${index}`} color={color} roughness={0.1} metalness={0.1} />
      ))}
    </mesh>
  );
};

export const RubikCube = () => {
  const [cubies] = useState(generateInitialCubies);
  const groupRef = useRef<THREE.Group>(null);
  const pivotRef = useRef<THREE.Group>(null);
  
  const rotationQueue = useRubikStore(state => state.rotationQueue);
  const dequeueRotation = useRubikStore(state => state.dequeueRotation);
  
  const [animating, setAnimating] = useState<RotationCommand | null>(null);
  const [animProgress, setAnimProgress] = useState(0);

  // Constants
  const ANIM_DURATION = 0.3; // seconds per 90deg turn

  useEffect(() => {
    if (!animating && rotationQueue.length > 0) {
      setAnimating(rotationQueue[0]);
      setAnimProgress(0);
      
      // Move relevant cubies to pivot
      const cmd = rotationQueue[0];
      const pivot = pivotRef.current;
      const group = groupRef.current;
      
      if (pivot && group) {
        pivot.rotation.set(0, 0, 0);
        
        // Find children that match the slice
        const childrenToMove = [];
        for (let i = group.children.length - 1; i >= 0; i--) {
          const child = group.children[i];
          const pos = new THREE.Vector3();
          child.getWorldPosition(pos);
          
          let match = false;
          if (cmd.slice === 'all') {
            match = true;
          } else {
            if (cmd.axis === 'x' && Math.round(pos.x) === cmd.slice) match = true;
            if (cmd.axis === 'y' && Math.round(pos.y) === cmd.slice) match = true;
            if (cmd.axis === 'z' && Math.round(pos.z) === cmd.slice) match = true;
          }
          
          if (match) {
            childrenToMove.push(child);
          }
        }
        
        // Move to pivot without changing world transform
        childrenToMove.forEach(child => pivot.attach(child));
      }
    }
  }, [rotationQueue, animating]);

  useFrame((_, delta) => {
    if (animating && pivotRef.current) {
      const newProgress = Math.min(1.0, animProgress + delta / ANIM_DURATION);
      setAnimProgress(newProgress);
      
      const angle = newProgress * (Math.PI / 2) * animating.direction;
      
      pivotRef.current.rotation.set(0, 0, 0);
      if (animating.axis === 'x') pivotRef.current.rotation.x = angle;
      if (animating.axis === 'y') pivotRef.current.rotation.y = angle;
      if (animating.axis === 'z') pivotRef.current.rotation.z = angle;

      if (newProgress >= 1.0) {
        // Animation complete
        const pivot = pivotRef.current;
        const group = groupRef.current;
        
        if (pivot && group) {
          pivot.updateMatrixWorld();
          // Move back to main group
          const childrenToMove = [...pivot.children];
          childrenToMove.forEach(child => {
            group.attach(child);
            // Snap coordinates to prevent floating point drift
            child.position.x = Math.round(child.position.x);
            child.position.y = Math.round(child.position.y);
            child.position.z = Math.round(child.position.z);
            
            child.rotation.x = Math.round(child.rotation.x / (Math.PI/2)) * (Math.PI/2);
            child.rotation.y = Math.round(child.rotation.y / (Math.PI/2)) * (Math.PI/2);
            child.rotation.z = Math.round(child.rotation.z / (Math.PI/2)) * (Math.PI/2);
          });
          pivot.rotation.set(0, 0, 0);
        }
        
        setAnimating(null);
        dequeueRotation();
      }
    }
  });

  return (
    <group>
      <group ref={groupRef}>
        {cubies.map((c) => (
          <Cubie key={c.id} data={c} />
        ))}
      </group>
      <group ref={pivotRef} />
    </group>
  );
};
