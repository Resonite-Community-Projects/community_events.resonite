document.addEventListener('alpine:init', () => {
    Alpine.data('metricsPage', () => ({
        summaryData: null,
        googleMapData: null,
        usersAverageCounterData: null,
        dailyUsersChartData: null,
        versionChartData: null,
        heatmapData: null,
        domainData: null,
        clientTypeData: null,
        loadingUsersAverageCounter: false,
        loadingGoogleMap: false,
        loadingDailyUsersChart: false,
        loadingVersionChart: false,
        loadingHeatmap: false,
        loadingDomains: false,
        loadingClientTypes: false,

        dailyUsersChart: null,
        versionChart: null,
        clientTypeChart: null,
        activityHeatmap: null,
        googleMap: null,
        domainCharts: [],

        async init() {
            await this.loadGoogleCharts();
            this.loadUsersAverageCounter();
            this.loadGoogleMap();
            this.loadDailyUsersChart();
            this.loadHeatmap();
            this.loadClientTypes();
            this.loadVersionChart();
            this.loadDomains();
            this.setupResizeHandlers();
        },

        loadGoogleCharts() {
            return new Promise((resolve) => {
                if (typeof google !== 'undefined' && google.visualization) {
                    resolve();
                    return;
                }

                google.charts.load('current', {
                    'packages': ['geochart']
                });

                google.charts.setOnLoadCallback(() => {
                    resolve();
                });
            });
        },

        async loadUsersAverageCounter() {
            this.loadingUsersAverageCounter = true;
            const response = await fetch('/v2/admin/metrics/users-average');
            this.usersAverageCounterData = await response.json();
            this.loadingUsersAverageCounter = false;
        },

        async loadDailyUsersChart() {
            this.loadingDailyUsersChart = true;
            const response = await fetch('/v2/admin/metrics/daily-users');
            this.dailyUsersChartData = await response.json();
            this.loadingDailyUsersChart = false;
            this.initDailyUsersChart();
        },

        async loadVersionChart() {
            this.loadingVersionChart = true;
            const response = await fetch('/v2/admin/metrics/client-versions');
            this.versionChartData = await response.json();
            this.loadingVersionChart = false;
            this.initVersionChart();
        },

        async loadGoogleMap() {
            this.loadingGoogleMap = true;
            const response = await fetch('/v2/admin/metrics/google-map');
            this.googleMapData = await response.json();
            this.loadingGoogleMap = false;
            this.initGoogleMap();
        },

        async loadHeatmap() {
            this.loadingHeatmap = true;
            const response = await fetch('/v2/admin/metrics/heatmap');
            this.heatmapData = await response.json();
            this.loadingHeatmap = false;
            setTimeout(() => {
                this.initHeatmapChart();
            }, 100);
        },

        async loadDomains() {
            this.loadingDomains = true;
            const response = await fetch('/v2/admin/metrics/domains');
            this.domainData = await response.json();
            this.loadingDomains = false;
            this.initDomainCharts();
        },

        async loadClientTypes() {
            this.loadingClientTypes = true;
            const response = await fetch('/v2/admin/metrics/client-types');
            this.clientTypeData = await response.json();
            this.loadingClientTypes = false;
            setTimeout(() => {
                this.initClientTypeChart();
            }, 100);
        },

        initGoogleMap() {
            if (!this.googleMapData?.country_data) { return; }

            const data = google.visualization.arrayToDataTable([
                ['Country', 'Users'],
                ...this.googleMapData.country_data.map(item => [item.name, item.value])
            ]);

            const options = { colorAxis: { colors: ['#e0ffff', '#006edd'] } };
            this.googleMap = new google.visualization.GeoChart(document.getElementById('regions_div'));
            this.googleMap.draw(data, options);
        },

        initDailyUsersChart() {
            const chartDom = document.getElementById('daily-users-chart');
            if (!chartDom) return;

            this.dailyUsersChart = echarts.init(chartDom);
            const option = {
                tooltip: {
                    trigger: 'axis',
                    formatter: '{b}: {c} users'
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: this.dailyUsersChartData.daily_unique_users_labels,
                    axisLabel: {
                        rotate: 45
                    },
                    boundaryGap: false
                },
                yAxis: {
                    type: 'value',
                    name: 'Unique Users'
                },
                series: [{
                    name: 'Unique Users',
                    type: 'line',
                    data: this.dailyUsersChartData.daily_unique_users_data,
                    smooth: true,
                    lineStyle: {
                        width: 3,
                        color: '#3298dc'
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(50, 152, 220, 0.5)' },
                            { offset: 1, color: 'rgba(50, 152, 220, 0.1)' }
                        ])
                    },
                    markPoint: {
                        data: [
                            { type: 'max', name: 'Max' },
                            { type: 'min', name: 'Min' }
                        ]
                    },
                    markLine: {
                        data: [{ type: 'average', name: 'Average' }]
                    }
                }]
            };
            this.dailyUsersChart.setOption(option);
        },

        initHeatmapChart() {
            if (!this.heatmapData) return;

            const chartDom = document.getElementById('activity-heatmap');
            if (!chartDom) return;

            this.activityHeatmap = echarts.init(chartDom);

            const transformedData = [];
            for (let day = 0; day < 7; day++) {
                for (let hour = 0; hour < 24; hour++) {
                    transformedData.push([hour, day, this.heatmapData.heatmap_data[day][hour]]);
                }
            }

            let minValue = Number.MAX_VALUE;
            let maxValue = 0;
            for (let day = 0; day < 7; day++) {
                for (let hour = 0; hour < 24; hour++) {
                    const value = this.heatmapData.heatmap_data[day][hour];
                    if (value < minValue) minValue = value;
                    if (value > maxValue) maxValue = value;
                }
            }

            const days = this.heatmapData.day_labels;
            const hours = this.heatmapData.hour_labels;

            const option = {
                tooltip: {
                    position: 'top',
                formatter: function (params) {
                    return `${days[params.value[1]]} at ${hours[params.value[0]]}<br>` +
                           `${params.value[2]} unique users`;
                }
                },
                grid: {
                    height: '70%',
                    top: '10%'
                },
                xAxis: {
                    type: 'category',
                    data: this.heatmapData.hour_labels,
                    splitArea: {
                        show: true
                    },
                    name: 'Hour of Day',
                    nameLocation: 'middle',
                    nameGap: 40,
                    axisLabel: {
                        interval: 2,
                        fontSize: 11
                    }
                },
                yAxis: {
                    type: 'category',
                    data: this.heatmapData.day_labels,
                    splitArea: {
                        show: true
                    },
                    name: 'Day of Week',
                    nameLocation: 'middle',
                    nameGap: 70
                },
                visualMap: {
                    min: minValue,
                    max: maxValue,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '0%',
                    text: ['High', 'Low'],
                    color: ['#d62728', '#2ca02c', '#98df8a', '#d9f0d3', '#f7f7f7'],
                    textStyle: {
                        color: '#333'
                    }
                },
                series: [{
                    name: 'User Activity',
                    type: 'heatmap',
                    data: transformedData,
                    label: {
                        show: true,
                        formatter: function(params) {
                            return params.value[2] > 0 ? params.value[2] : '';
                        }
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }]
            };

            this.activityHeatmap.setOption(option);

        },

        initClientTypeChart() {
            if (!this.clientTypeData) return;

            const chartDom = document.getElementById('client-type-chart-container');
            if (!chartDom) return;

            this.clientTypeChart = echarts.init(chartDom);
            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{b}: {c} ({d}%)'
                },
                series: [{
                    name: 'Client Type Distribution',
                    type: 'pie',
                    radius: '70%',
                    itemStyle: {
                        borderRadius: 5,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        formatter: '{b}: {d}%',
                        show: true
                    },
                    data: this.clientTypeData.map(item => ({
                        name: item.client || 'Unknown',
                        value: item.count
                    }))
                }]
            };
            this.clientTypeChart.setOption(option);
        },

        initVersionChart() {
            const chartDom = document.getElementById('version-chart-container');
            if (!chartDom) return;

            this.versionChart = echarts.init(chartDom);
            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{b}: {c} ({d}%)'
                },
                series: [{
                    name: 'Version Distribution',
                    type: 'pie',
                    radius: '70%',
                    itemStyle: {
                        borderRadius: 5,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        formatter: '{b}: {d}%',
                        show: true
                    },
                    data: this.versionChartData.versions.map(item => ({
                        name: item.version || 'Unknown',
                        value: item.count
                    }))
                }]
            };
            this.versionChart.setOption(option);
        },

        initDomainCharts() {

            // Wait for Alpine.js to render the template
            setTimeout(() => {

                Object.entries(this.domainData || {}).forEach(([domain, metrics], index) => {

                    const sanitizedDomain = domain.replace(/\./g, '-');
                    const elementId = `domain-chart-${sanitizedDomain}`;

                    const chartDom = document.getElementById(elementId);

                    if (!chartDom) { return; }

                    const chart = echarts.init(chartDom);

                    const data = metrics.counts.map(item => ({
                        name: item.endpoint,
                        value: item.count
                    }));

                    const option = {
                        tooltip: {
                            trigger: 'item',
                            formatter: '{b}: {c} ({d}%)'
                        },
                        series: [{
                            name: 'Endpoints',
                            type: 'pie',
                            radius: '70%',
                            itemStyle: {
                                borderRadius: 5,
                                borderColor: '#fff',
                                borderWidth: 2
                            },
                            label: {
                                formatter: '{b}: {d}%',
                                show: true
                            },
                            data: data
                        }]
                    };

                    chart.setOption(option);

                    this.domainCharts = this.domainCharts || [];
                    this.domainCharts.push(chart);
                });

            }, 500);
        },

        getClientTypeTotal() {
            return (this.clientTypeData || []).reduce((sum, ct) => sum + ct.count, 0);
        },

        getClientTypePercentage(clientType) {
            const total = this.getClientTypeTotal();
            return total > 0 ? Math.round((clientType.count / total) * 100) : 0;
        },

        getVersionTotal() {
            return (this.versionChartData?.versions || []).reduce((sum, v) => sum + v.count, 0);
        },

        getVersionPercentage(version) {
            const total = this.getVersionTotal();
            return total > 0 ? Math.round((version.count / total) * 100) : 0;
        },

        getDomainPercentage(count, total) {
            return total > 0 ? Math.round((count / total) * 100) : 0;
        },

        setupResizeHandlers() {
            window.addEventListener('resize', () => {
                if (this.dailyUsersChart) this.dailyUsersChart.resize();
                if (this.versionChart) this.versionChart.resize();
                if (this.clientTypeChart) this.clientTypeChart.resize();
                if (this.activityHeatmap) this.activityHeatmap.resize();
                if (this.domainCharts) {
                    this.domainCharts.forEach(chart => chart.resize());
                }
            });
        },

    }))
});
