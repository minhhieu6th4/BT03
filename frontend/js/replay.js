const BOARD_SIZE = 9;
if (typeof API_BASE === 'undefined') {
    var API_BASE = window.location.origin.includes('5500')
        ? window.location.origin.replace(':5500', ':5000')
        : (window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : window.location.origin);
}

// RED: 1(ROCK), 2(PAPER), 3(SCISSORS)
// BLUE: 4(ROCK), 5(PAPER), 6(SCISSORS)
const pieceMap = {
    1: { char: '🪨', class: 'piece-red' },
    2: { char: '📄', class: 'piece-red' },
    3: { char: '✂️', class: 'piece-red' },
    4: { char: '🪨', class: 'piece-blue' },
    5: { char: '📄', class: 'piece-blue' },
    6: { char: '✂️', class: 'piece-blue' }
};

let currentBoard = [];

function initializeBoard() {
    const boardDiv = document.getElementById('board');
    boardDiv.innerHTML = '';
    currentBoard = [];
    
    for (let r = 0; r < BOARD_SIZE; r++) {
        let row = [];
        for (let c = 0; c < BOARD_SIZE; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.id = `cell-${r}-${c}`;
            
            // Đánh dấu ô đích đến của từng phe
            if (r === 0 && c === 0) cell.classList.add('red-dest');
            if (r === BOARD_SIZE - 1 && c === BOARD_SIZE - 1) cell.classList.add('blue-dest');
            
            boardDiv.appendChild(cell);
            row.push(0);
        }
        currentBoard.push(row);
    }
}

function renderBoard(boardState) {
    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            const val = boardState[r][c];
            const cell = document.getElementById(`cell-${r}-${c}`);
            if (val === 0) {
                cell.innerHTML = '';
            } else {
                cell.innerHTML = `<span class="${pieceMap[val].class}">${pieceMap[val].char}</span>`;
            }
            currentBoard[r][c] = val;
        }
    }
}

function renderMove(move) {
    const r1 = move.from[0], c1 = move.from[1];
    const r2 = move.to[0], c2 = move.to[1];
    
    const movingPiece = currentBoard[r1][c1];
    
    // Xóa quân ở vị trí cũ
    currentBoard[r1][c1] = 0;
    
    // Chuyển quân sang vị trí mới. 
    // Trong thực tế, frontend cần update mảng bàn cờ dựa vào kết quả combat từ backend 
    // (tức là file json cung cấp trạng thái bàn cờ từng bước).
    // Tuy nhiên MVP ta sẽ di chuyển quân tạm thời.
    currentBoard[r2][c2] = movingPiece;
    
    renderBoard(currentBoard);
}

// Hàm Sleep quan trọng nhất - Delay 3 giây theo yêu cầu
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function playReplay(matchData) {
    document.getElementById('team-names').innerText = `${matchData.red_team} (RED) vs ${matchData.blue_team} (BLUE)`;
    document.getElementById('match-status').innerText = 'Playing... (3s delay per move)';
    
    renderBoard(matchData.initial_board);
    
    // Play moves with EXACTLY 3 seconds display delay
    for (const move of matchData.moves) {
        await sleep(3000);
        renderMove(move);
    }
    
    document.getElementById('match-status').innerText = `Finished! Result: ${matchData.result.winner} won. (${matchData.result.reason})`;
}

// Tự động tải danh sách trận đấu từ match_logs (Cây giải đấu)
async function loadTournamentDropdown() {
    const select = document.getElementById('tournamentSelect');
    if (!select) return;

    try {
        const response = await fetch(`${API_BASE}/api/matches/tree`);
        if (!response.ok) return;
        const stages = await response.json();

        // Xóa các option cũ ngoại trừ option mặc định
        select.innerHTML = '<option value="">🏆 -- Chọn trận đấu giải đấu từ match_logs --</option>';

        stages.forEach(s => {
            const stageOptgroup = document.createElement('optgroup');
            const stageLabels = {
                'qualification': 'Vòng Bảng (Qualification)',
                'round_of_32': 'Vòng 32 Đội (Round of 32)',
                'round_of_16': 'Vòng 16 Đội (Round of 16)',
                'quarterfinal': 'Tứ Kết (Quarterfinal)',
                'semifinal': 'Bán Kết (Semifinal)',
                'final': 'Chung Kết (Grand Final)'
            };
            stageOptgroup.label = stageLabels[s.stage] || s.stage.toUpperCase();

            // Nhóm có groups (như qualification)
            if (s.groups && s.groups.length > 0) {
                s.groups.forEach(g => {
                    g.matches.forEach(m => {
                        const red = m.red_team?.name || 'RED';
                        const blue = m.blue_team?.name || 'BLUE';
                        const score = m.score ? `${m.score.red}-${m.score.blue}` : '';
                        
                        if (m.games && m.games.length > 0) {
                            m.games.forEach(game => {
                                const opt = document.createElement('option');
                                opt.value = game.file_path;
                                opt.textContent = `[${g.group}] ${m.match_id} (${red} vs ${blue} [${score}]) - ${game.game_id}`;
                                stageOptgroup.appendChild(opt);
                            });
                        }
                    });
                });
            }

            // Nhóm match trực tiếp (Knockout)
            if (s.matches && s.matches.length > 0) {
                s.matches.forEach(m => {
                    const red = m.red_team?.name || 'RED';
                    const blue = m.blue_team?.name || 'BLUE';
                    const score = m.score ? `${m.score.red}-${m.score.blue}` : '';

                    if (m.games && m.games.length > 0) {
                        m.games.forEach(game => {
                            const opt = document.createElement('option');
                            opt.value = game.file_path;
                            opt.textContent = `${m.match_id} (${red} vs ${blue} [${score}]) - ${game.game_id}`;
                            stageOptgroup.appendChild(opt);
                        });
                    } else {
                        const opt = document.createElement('option');
                        opt.value = `${m.path}/match.json`;
                        opt.textContent = `${m.match_id} (${red} vs ${blue} [${score}]) [Summary Only]`;
                        stageOptgroup.appendChild(opt);
                    }
                });
            }

            if (stageOptgroup.children.length > 0) {
                select.appendChild(stageOptgroup);
            }
        });
    } catch (e) {
        console.warn("Không thể tải cây giải đấu (Backend chưa bật):", e);
    }
}

async function onSelectTournamentMatch() {
    const select = document.getElementById('tournamentSelect');
    const path = select.value;
    if (!path) return;

    if (path.endsWith('match.json')) {
        alert("Cặp đấu này chỉ lưu tổng kết match.json (chưa có file log ván đấu riêng lẻ).");
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/matches/replay-by-path?path=${encodeURIComponent(path)}`);
        if (!response.ok) throw new Error("Không thể tải file replay theo đường dẫn");
        const data = await response.json();
        await playReplay(data);
    } catch (e) {
        alert("Lỗi tải replay: " + e.message);
    }
}

async function loadReplay() {
    const gameId = document.getElementById('gameIdInput').value || 'game_01';
    try {
        const response = await fetch(`${API_BASE}/api/matches/game/${gameId}/replay`);
        if (!response.ok) throw new Error("Replay not found or Server not running");
        
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        
        await playReplay(data);
    } catch (e) {
        alert("Could not load replay: " + e.message);
    }
}

async function triggerMatch() {
    try {
        const response = await fetch(`${API_BASE}/api/matches/run?team_a_id=1&team_b_id=2`, { method: 'POST' });
        const result = await response.json();
        if(response.ok) {
            alert(result.message + "\n\nHãy đợi vài giây rồi bấm xem Replay nhé!");
        } else {
            alert("Lỗi: " + result.error);
        }
    } catch(e) {
        alert("Lỗi kết nối Backend.");
    }
}

// Khởi tạo bàn cờ
initializeBoard();

