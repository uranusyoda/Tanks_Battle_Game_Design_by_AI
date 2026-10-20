// DOM HUD. Owns the overlay, score bars and messages. It renders state; it
// does not decide state.

const $ = (id) => document.getElementById(id);

export function createHud({ tanks }) {
  const overlay = $('overlay');
  const msg = $('msg');
  let mode = 'garage';
  let msgTimer = 0;
  let onPick = () => {};
  let onGarage = () => {};

  overlay.addEventListener('click', (event) => {
    if (mode === 'garage') {
      const card = event.target.closest('.card');
      if (card) onPick(card.dataset.tank);
    } else if (mode === 'over') {
      onGarage();
    }
  });

  function showLoading(text = '正在装载 M4A1 Sherman…') {
    mode = 'loading';
    document.body.classList.remove('garage-mode');
    overlay.className = '';
    overlay.style.display = 'flex';
    overlay.innerHTML = `<div class="panel"><h1>钢铁防线 <span>3D</span></h1>
      <div class="sub">${text}</div>
      <div class="loader"><div></div></div></div>`;
  }

  function showGarage() {
    mode = 'garage';
    document.body.classList.add('garage-mode');
    overlay.style.display = 'flex';
    overlay.className = 'garage';
    overlay.innerHTML = `<div class="panel">
      <h1>钢铁防线 <span>3D</span></h1>
      <div class="sub">Sherman Edition · 三辆可选坦克统一使用 M4A1 车体与动画 · 资产 / 玩法分层版本</div>
      <div class="cards">${Object.entries(tanks)
        .map(
          ([id, t]) => `
        <div class="card" data-tank="${id}">
          <h3>${t.name}</h3><div class="era">${t.cls}</div>
          <div class="stat"><span>HP</span><b>${t.hp}</b></div>
          <div class="stat"><span>速度</span><b>${t.speed}</b></div>
          <div class="stat"><span>射速</span><b>${t.fire}s</b></div>
          <div class="stat"><span>伤害</span><b>${t.dmg}</b></div>
          <div class="skill"><b>${t.skill.name} [E]</b>${t.skill.desc}</div>
        </div>`,
        )
        .join('')}
      </div>
      <div class="sub" style="margin-top:22px">W/S 前进后退 · A/D 车体转向 · 鼠标瞄准 · 空格/点击开火 · E 技能 · C 切换俯视角 · R 返回车库<br>
      守住底部鹰徽，消灭 3 波共 10 辆敌军。小心：任何炮弹——包括你自己的——命中鹰徽即告失败！</div>
    </div>`;
  }

  function hide() {
    document.body.classList.remove('garage-mode');
    overlay.className = '';
    overlay.style.display = 'none';
    mode = 'battle';
  }

  function showGameOver({ win, reason, score, hi }) {
    mode = 'over';
    document.body.classList.remove('garage-mode');
    overlay.className = '';
    overlay.style.display = 'flex';
    overlay.innerHTML = `<div class="panel">
      <h1 style="color:${win ? '#7dc95e' : '#e4573d'}">${win ? '胜利!' : '防线失守'}</h1>
      <div class="sub">${reason} · 得分 ${score} · 最高分 ${hi}</div>
      <div class="sub" style="font-size:15px;color:#f2e8c9">点击任意处返回车库</div>
    </div>`;
  }

  function flash(text) {
    msg.textContent = text;
    msg.style.opacity = 1;
    msgTimer = 2;
  }

  function initIcons(total) {
    const el = $('enemyIcons');
    el.innerHTML = '';
    for (let i = 0; i < total; i++) {
      const d = document.createElement('div');
      d.className = 'eic';
      el.appendChild(d);
    }
  }

  function update(state, dt) {
    if (msgTimer > 0) {
      msgTimer -= dt;
      if (msgTimer <= 0) msg.style.opacity = 0;
    }
    if (!state) return;
    const p = state.player;
    $('score').textContent = state.score;
    $('lives').textContent = p.lives;
    $('hpbar').style.width = `${(p.hp / p.maxHp) * 100}%`;
    $('ecount').textContent = state.totalEnemies - state.killed;
    const icons = $('enemyIcons').children;
    for (let i = 0; i < icons.length; i++) icons[i].classList.toggle('dead', i < state.killed);

    const cd = Math.max(0, state.skillCd);
    $('skillFill').style.height = cd > 0 ? `${(cd / p.spec.skill.cd) * 100}%` : '0%';
    $('skillName').textContent = p.spec.skill.name;
    let status = '就绪 [E]';
    if (cd > 0) status = `冷却 ${cd.toFixed(1)}s`;
    if (p.smoke > 0) status = `烟幕中 ${p.smoke.toFixed(1)}s`;
    if (p.ap) status = '穿甲弹已装填!';
    if (p.reactiveLeft > 0) status = `反应装甲 x${p.reactiveLeft}`;
    $('skillState').textContent = status;
  }

  function setHighScore(hi) {
    $('hiscore').textContent = hi;
  }

  return {
    showLoading,
    showGarage,
    hide,
    showGameOver,
    flash,
    initIcons,
    update,
    setHighScore,
    onPick(fn) {
      onPick = fn;
    },
    onGarage(fn) {
      onGarage = fn;
    },
    get mode() {
      return mode;
    },
  };
}
