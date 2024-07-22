# Script to read and analyse data exported from Earth Engine

# Libraries
library(car)
library(dplyr)
library(ggplot2)
library(lubridate)
library(ggpubr)

# Arrange data
# Landsat
df1 = read.csv("../data/vi_gee/Landsat/non_protected.csv") %>%
  mutate(vi = as.factor(vi),
         lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date),
         state = 'Non-Protected') %>%
  group_by(fileID, pointID, vi, lat, lon, date, state) %>%
  summarise(values = mean(target)) %>%
  as.data.frame() %>%
  dplyr::select(state, vi, lat, lon, date, values)
df2 = read.csv("../data/vi_gee/Landsat/protected.csv") %>%
  mutate(vi = as.factor(vi),
         lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date),
         state = 'Protected') %>%
  group_by(fileID, pointID, vi, lat, lon, date, state) %>%
  summarise(values = mean(target)) %>%
  as.data.frame() %>%
  dplyr::select(state, vi, lat, lon, date, values)

landsat = bind_rows(df1, df2)
rm(df1, df2); gc()

saveRDS(landsat, file = "../data/vi_gee/Landsat_vi.rds")

# MODIS
df1 = read.csv("../data/vi_gee/MODIS/NDVI_in_one.csv") %>%
  dplyr::select(state, lat, lon, NDVI = target, date) %>%
  mutate(lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date)) %>%
  group_by(lat, lon, date, state) %>%
  summarise(NDVI = mean(NDVI))
df2 = read.csv("../data/vi_gee/MODIS/EVI_in_one.csv") %>%
  dplyr::select(state, lat, lon, EVI = target, date) %>%
  mutate(lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date)) %>%
  group_by(lat, lon, date, state) %>%
  summarise(EVI = mean(EVI))

modis = full_join(df1, df2, by = c('lat', 'lon', 'state', 'date'))
modis$state[which(modis$state == "")] = "Not_Defined"
rm(df1, df2); gc()

modis %>% group_by(state) %>% 
  summarise(mean_ndvi = mean(NDVI, na.rm=T), sd_ndvi = sd(NDVI, na.rm=T), 
            mean_evi = mean(EVI), sd_evi = sd(EVI))

saveRDS(modis, file = "../data/vi_gee/MODIS_vi.rds")

#
seasons_LUT = data.frame(months = 1:12,
                         season = c(rep('Winter', 2),
                                    rep('Spring', 3),
                                    rep('Summer', 3),
                                    rep('Autumn', 3),
                                    'Winter'))

landsat = landsat %>% mutate(months = month(date)) %>% 
  left_join(seasons_LUT, by = 'months') %>%
  mutate(state = factor(state, levels = c('Protected', 'Non-Protected')),
         vi = factor(vi, levels = c('ndvi', 'nirv'), labels = c('NDVI', 'NIRv')),
         season = factor(season, levels = c('Spring', 'Summer', 'Autumn', 'Winter')))

# seasonal differences
ggplot(landsat, aes(x = lat, y = values, color = season, fill = season)) +
  geom_hline(yintercept = 0, linetype = 'dotted', color = 'grey90') +
  geom_smooth() +
  facet_wrap(~vi, nrow = 1, ncol = 2, scales = 'free') +
  theme_classic() +
  theme(legend.position = 'top')

p1 = ggplot(landsat %>% 
              subset(date >= ym('1999-01') & date < ym('2009-01') & 
                       vi == 'nirv' & season == 'Summer'),
       aes(x = lat, y = values, color = state, fill = state)) +
  #geom_point(shape = 16, alpha = 0.1) +
  geom_smooth() +
  theme_classic()
p2 = ggplot(landsat %>% 
              subset(date >= ym('2009-01') & date < ym('2019-01')  & 
                       vi == 'nirv' & season == 'Summer'),
            aes(x = lat, y = values, color = state, fill = state)) +
  #geom_point(shape = 16, alpha = 0.1) +
  geom_smooth() +
  theme_classic()
ggarrange(p1, p2, nrow = 1, ncol = 2, common.legend = T)
