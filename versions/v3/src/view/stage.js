// Renderer, sky, lighting and the non-interactive scenery. This is the only
// module that owns the WebGL renderer; mechanics never import it.

import * as THREE from 'three';
import { createSurfaceTextures, createFxTextures, makeSkyEquirect } from '../assets/procedural.js';

const SUN_DIR = new THREE.Vector3(9, 15, 6).normalize();

export function createStage(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const maxAniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const surfaceTextures = createSurfaceTextures(maxAniso);
  const fxTextures = createFxTextures(maxAniso);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xdfcdad);
  scene.fog = new THREE.Fog(0xdfcdad, 30, 115);

  const camera = new THREE.PerspectiveCamera(58, innerWidth / innerHeight, 0.1, 600);

  function onResize() {
    renderer.setSize(innerWidth, innerHeight);
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
  }
  addEventListener('resize', onResize);
  onResize();

  // image based lighting from a painted sky
  const skyEquirect = new THREE.CanvasTexture(makeSkyEquirect(SUN_DIR));
  skyEquirect.mapping = THREE.EquirectangularReflectionMapping;
  skyEquirect.colorSpace = THREE.SRGBColorSpace;
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();
  const prevToneMapping = renderer.toneMapping;
  renderer.toneMapping = THREE.NoToneMapping;
  scene.environment = pmrem.fromEquirectangular(skyEquirect).texture;
  renderer.toneMapping = prevToneMapping;
  pmrem.dispose();

  const skyMat = new THREE.ShaderMaterial({
    uniforms: {
      uTop: { value: new THREE.Color('#2a5b95') },
      uMid: { value: new THREE.Color('#82aed6') },
      uHorizon: { value: new THREE.Color('#e9d5b2') },
      uGround: { value: new THREE.Color('#a08057') },
      uSun: { value: new THREE.Color('#ffe6b4') },
      uSunDir: { value: SUN_DIR.clone() },
    },
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    vertexShader: /* glsl */ `
      varying vec3 vDir;
      void main(){
        vDir = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uTop, uMid, uHorizon, uGround, uSun, uSunDir;
      varying vec3 vDir;
      void main(){
        vec3 d = normalize(vDir);
        float h = d.y;
        vec3 col;
        if(h >= 0.0){
          col = mix(uHorizon, uMid, smoothstep(0.0, 0.14, h));
          col = mix(col, uTop, smoothstep(0.10, 0.62, h));
        } else {
          col = mix(uHorizon, uGround, smoothstep(0.0, 0.20, -h));
        }
        float s = max(dot(d, uSunDir), 0.0);
        col += uSun * pow(s, 720.0) * 5.0;
        col += uSun * pow(s, 24.0) * 0.30;
        col += uSun * pow(s, 3.0) * 0.10;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });

  const sky = new THREE.Mesh(new THREE.SphereGeometry(260, 40, 20), skyMat);
  sky.frustumCulled = false;
  sky.renderOrder = -1;
  scene.add(sky);

  scene.add(new THREE.HemisphereLight(0xcfe0ff, 0x6b5436, 0.5));
  const sun = new THREE.DirectionalLight(0xffe2b4, 2.5);
  sun.position.copy(SUN_DIR).multiplyScalar(24);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -11;
  sun.shadow.camera.right = 11;
  sun.shadow.camera.top = 11;
  sun.shadow.camera.bottom = -11;
  sun.shadow.camera.near = 2;
  sun.shadow.camera.far = 60;
  sun.shadow.camera.updateProjectionMatrix();
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.03;
  scene.add(sun);

  const fillLight = new THREE.DirectionalLight(0x9dc0ea, 0.65);
  fillLight.position.set(-10, 7, -8);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0xffb27a, 0.45);
  rimLight.position.set(-3, 4, 12);
  scene.add(rimLight);

  // ------------------------------------------------------------------ ground
  const groundMat = new THREE.MeshStandardMaterial({
    map: surfaceTextures.groundMap,
    normalMap: surfaceTextures.groundNormal,
    normalScale: new THREE.Vector2(0.65, 0.65),
    roughnessMap: surfaceTextures.groundRough,
    roughness: 1,
    metalness: 0,
    envMapIntensity: 0.4,
  });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(240, 240), groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const geoDune = new THREE.SphereGeometry(1, 20, 10);
  const geoRock = new THREE.DodecahedronGeometry(0.5, 0);
  const geoShrub = new THREE.IcosahedronGeometry(0.4, 0);

  (function buildScenery() {
    const duneMat = new THREE.MeshStandardMaterial({ color: 0xc2a476, roughness: 1, metalness: 0 });
    for (let i = 0; i < 11; i++) {
      const a = (i / 11) * Math.PI * 2 + 0.35;
      const d = 54 + Math.random() * 36;
      const m = new THREE.Mesh(geoDune, duneMat);
      m.position.set(Math.cos(a) * d, -7 - Math.random() * 2, Math.sin(a) * d);
      m.scale.set(24 + Math.random() * 22, 10 + Math.random() * 7, 16 + Math.random() * 12);
      m.rotation.y = Math.random() * Math.PI;
      scene.add(m);
    }

    const rockMat = new THREE.MeshStandardMaterial({
      color: 0x9d8b70, roughness: 0.92, metalness: 0.04, flatShading: true,
    });
    const rocks = new THREE.InstancedMesh(geoRock, rockMat, 110);
    const dummy = new THREE.Object3D();
    for (let i = 0; i < 110; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = 8.2 + Math.pow(Math.random(), 0.75) * 34;
      const s = 0.1 + Math.pow(Math.random(), 2) * 0.7;
      dummy.position.set(Math.cos(a) * r, s * 0.24, Math.sin(a) * r);
      dummy.rotation.set(Math.random() * 3.14, Math.random() * 6.28, Math.random() * 3.14);
      dummy.scale.set(s, s * (0.55 + Math.random() * 0.6), s * (0.8 + Math.random() * 0.4));
      dummy.updateMatrix();
      rocks.setMatrixAt(i, dummy.matrix);
    }
    rocks.castShadow = true;
    rocks.receiveShadow = true;
    rocks.instanceMatrix.needsUpdate = true;
    scene.add(rocks);

    const shrubMat = new THREE.MeshStandardMaterial({
      color: 0xffffff, roughness: 1, metalness: 0, flatShading: true,
    });
    const shrubs = new THREE.InstancedMesh(geoShrub, shrubMat, 80);
    const col = new THREE.Color();
    for (let i = 0; i < 80; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = 8.4 + Math.pow(Math.random(), 0.8) * 26;
      const s = 0.5 + Math.random() * 0.9;
      dummy.position.set(Math.cos(a) * r, s * 0.16, Math.sin(a) * r);
      dummy.rotation.set(0, Math.random() * 6.28, 0);
      dummy.scale.set(s, s * 0.42, s);
      dummy.updateMatrix();
      shrubs.setMatrixAt(i, dummy.matrix);
      col.setHSL(0.13 + Math.random() * 0.06, 0.28 + Math.random() * 0.18, 0.22 + Math.random() * 0.13);
      shrubs.setColorAt(i, col);
    }
    shrubs.castShadow = true;
    shrubs.instanceMatrix.needsUpdate = true;
    if (shrubs.instanceColor) shrubs.instanceColor.needsUpdate = true;
    scene.add(shrubs);
  })();

  // drifting dust motes
  const DUST_N = 260;
  const dustPos = new Float32Array(DUST_N * 3);
  const dustBase = new Float32Array(DUST_N * 3);
  const dustPhase = new Float32Array(DUST_N);
  for (let i = 0; i < DUST_N; i++) {
    dustBase[i * 3] = (Math.random() - 0.5) * 26;
    dustBase[i * 3 + 1] = 0.25 + Math.random() * 5.5;
    dustBase[i * 3 + 2] = (Math.random() - 0.5) * 26;
    dustPhase[i] = Math.random() * 6.283;
  }
  dustPos.set(dustBase);
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
  const dustPoints = new THREE.Points(
    dustGeo,
    new THREE.PointsMaterial({
      map: fxTextures.smokeTex,
      size: 0.11,
      color: 0xffe6c2,
      transparent: true,
      opacity: 0.32,
      depthWrite: false,
      sizeAttenuation: true,
      alphaTest: 0.02,
    }),
  );
  dustPoints.frustumCulled = false;
  scene.add(dustPoints);

  // pointer -> ground plane picking for aiming
  const raycaster = new THREE.Raycaster();
  const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const ndc = new THREE.Vector2();
  const pickOut = new THREE.Vector3();

  /** Writes {x,y,z} into `out` when the pointer ray meets the ground. */
  function pickGround(point, out = pickOut) {
    ndc.set(point.x, point.y);
    raycaster.setFromCamera(ndc, camera);
    const hit = raycaster.ray.intersectPlane(groundPlane, pickOut);
    if (!hit) return null;
    out.x = pickOut.x;
    out.y = pickOut.y;
    out.z = pickOut.z;
    return out;
  }

  function update(dt, time) {
    for (let i = 0; i < DUST_N; i++) {
      const ph = dustPhase[i];
      dustPos[i * 3] = dustBase[i * 3] + Math.sin(time * 0.25 + ph) * 0.9;
      dustPos[i * 3 + 1] = dustBase[i * 3 + 1] + Math.sin(time * 0.45 + ph * 1.7) * 0.5;
      dustPos[i * 3 + 2] = dustBase[i * 3 + 2] + Math.cos(time * 0.21 + ph) * 0.9;
    }
    dustGeo.attributes.position.needsUpdate = true;
    sky.position.copy(camera.position);
  }

  function render() {
    renderer.render(scene, camera);
  }

  return {
    renderer,
    scene,
    camera,
    sun,
    sky,
    surfaceTextures,
    fxTextures,
    pickGround,
    update,
    render,
  };
}
