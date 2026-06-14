const API_KEY = process.env.FOOTBALL_DATA_API_KEY;
const BASE    = 'https://api.football-data.org/v4';

export default async (req, context) => {
  if (!API_KEY) {
    return new Response(JSON.stringify({ error: 'API key not configured' }), {
      status: 500, headers: { 'Content-Type': 'application/json' }
    });
  }

  const headers = { 'X-Auth-Token': API_KEY };

  try {
    const [rMatches, rStandings] = await Promise.all([
      fetch(BASE + '/competitions/WC/matches', { headers }),
      fetch(BASE + '/competitions/WC/standings', { headers }),
    ]);

    const matchData    = await rMatches.json();
    const standingData = await rStandings.json();

    const results = {};
    for (const m of matchData.matches || []) {
      if (m.status === 'FINISHED') {
        const key = m.homeTeam.tla + '-' + m.awayTeam.tla;
        results[key] = { home: m.score.fullTime.home, away: m.score.fullTime.away };
      }
    }

    const standings = {};
    for (const g of standingData.standings || []) {
      const letter = g.group.replace('Group ', '');
      standings[letter] = g.table.map(t => ({
        pos: t.position, tla: t.team.tla, nome: t.team.shortName,
        pj: t.playedGames, v: t.won, e: t.draw, d: t.lost,
        gf: t.goalsFor, gc: t.goalsAgainst, dg: t.goalDifference, pts: t.points,
      }));
    }

    return new Response(JSON.stringify({ results, standings }), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=60',
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 502, headers: { 'Content-Type': 'application/json' }
    });
  }
};

export const config = { path: '/api/results' };
