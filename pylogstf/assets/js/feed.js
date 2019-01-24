var Logs = {
    data: {},
    title: "",
    tf2map: "",
    format: "",
    players: [],
    page: 1,
    refresh: function() {
        Logs.data = {};
        let plrs = Logs.players.join(',');
        let url = "/api/v1/log?limit=20&offset="+((Logs.page-1)*20)+"&title="+Logs.title+"&map="+Logs.tf2map+"&format="+Logs.format+"&player="+plrs;
        console.log(url);
        m.request({
            method: "GET",
            url: url,

        })
        .then(function(data) {
            Logs.data = data;
        })
    },
    nextPage: function() {
        Logs.page += 1;
        Logs.refresh();
    },
    prevPage: function() {
        if (Logs.page > 1) {
            Logs.page -= 1;
            Logs.refresh();
        }
    },
    setTitle: function(title) {
        if (title.length > 2) {
            Logs.title = title;
        } else {
            Logs.title = "";
        }
        Logs.page = 1;
        Logs.refresh();
    },
    setMap: function(tf2map) {
        if (tf2map.length > 2) {
            Logs.tf2map = tf2map;
        } else {
            Logs.tf2map = "";
        }
        Logs.page = 1;
        Logs.refresh();
    },
    setFormat: function(format) {
        Logs.format = format;
        Logs.page = 1;
        Logs.refresh();
    },
    getFormat: function(players) {
        if (players >= 18)
            return "Highlander";
        if (players >= 12)
            return "6v6"
        if (players >= 8)
            return "4v4";
        if (players >= 4)
            return "2v2";
        return "1v1";
    },
    removePlayer: function(player) {
        Logs.players = Logs.players.filter(item => item !== player);
        Logs.refresh();
    },
    addPlayer: function (player) {
        if (Logs.players.indexOf(player) == -1) {
            Logs.players.push(player);
            Search.clear();
            Logs.refresh();
        }
    }
}

var Search = {
    name: "",
    result: {},
    refresh: function() {
        m.request({
            method: "GET",
            url: "/api/v1/player_search?name="+Search.name
        })
        .then(function(data) {
            Search.result = data;
        })
    },
    clear: function() {
        Search.result = {};
    }
}

var Feed = {
    view: function() {
        var items = [];

        if (Logs.data && Logs.data.logs) {
            for (item of Logs.data.logs) {
                var el = m("tr", [
                    m("td", m("a", {
                        href: '/'+item.id
                     }, item.title)),
                    m("td", item.map),
                    m("td", Logs.getFormat(item.players)),
                    m("td", item.views),
                    m("td", moment.unix(item.date).format('lll')),
                ]);
                items.push(el);
            }
        } else {
            items = [m("h3", "Loading...")]
        }


        var players = [];
        for (p of Logs.players) {
            var el = m("div", [
                m("span.label.label-default", p),
                m("button", {
                    onclick: Logs.removePlayer.bind(Logs, p)
                }, "-"),
            ]);
            players.push(el);
        }

        var player_search_results = [];
        if (Search.result.players) {
            player_search_results.push(m("button", { onclick: Search.clear.bind(Search) }, "Close"))
            for (p of Search.result.players) {
                var el = m("div[style=font-size:10px]", [
                    m("span", p.names+" "),
                    m("button", {
                        onclick: Logs.addPlayer.bind(Logs, p.id)
                    }, "+"),
                ]);
                player_search_results.push(el);
            }
        }


        var player_search = [
            m("div", {
                style: {
                    position: "relative",
                    display: "inline-block",
                }
            }, [
                m("input[type=text][placeholder=Search players]", {
                    oninput: m.withAttr("value", function (value) { Search.name = value }),
                }),
                m("input[type=submit][value=Search]", {
                    onclick: function() {
                        Search.refresh();
                    }
                }),
            ]),
            m("div", {
                style: {
                    position: 'absolute',
                    background: '#EEE',
                }
            }, [
                player_search_results,
            ]),
        ];


        return m("div", [
            m("div.controls", [
                m("input.controls-title[type=text][placeholder=Search logs]", {
                    oninput: m.withAttr("value", function(value) {Logs.setTitle(value)}),
                }),
                m("input.controls-map[type=text][placeholder=Search map]", {
                    oninput: m.withAttr("value", function(value) {Logs.setMap(value)}),
                }),
                m("select.controls-format", {
                    oninput: m.withAttr("value", function(value) {Logs.setFormat(value)}),
                }, [
                    m("option", "All formats"),
                    m("option[value=6v6]", "6v6"),
                    m("option[value=highlander]", "Highlander"),
                    m("option[value=4v4]", "4v4"),
                    m("option[value=2v2]", "2v2"),
                    m("option[value=1v1]", "Duel"),
                ]),
                player_search,
                players,
            ]),
            m("table", {class: "table loglist"}, [
                m("thead", [
                    m("tr", [
                        m("th", {class: "feed-title"}, "Title"),
                        m("th", {class: "feed-map"}, "Map"),
                        m("th", {class: "feed-format"}, "Format"),
                        m("th", {class: "feed-views"}, "Views"),
                        m("th", {class: "feed-date"}, "Date"),
                    ])
                ]),
                m("tbody", items)
            ]),
            m("div", "Page: " + Logs.page),
            m("div", "Total: " + Logs.data.total),
            m("span", {onclick: Logs.prevPage}, "Previous"),
            m("span", {onclick: Logs.nextPage}, "Next"),
        ])
    }
}

Logs.refresh();

m.mount(document.getElementById('feed'), Feed);

