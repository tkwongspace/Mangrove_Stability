# Script to read and analyse data exported from Earth Engine

# Libraries
library(dplyr)
library(ggplot2)
library(lubridate)
library(ggpubr)

# Arrange data
# Landsat
df1 = read.csv("../data/vi_gee/Landsat/NDVI_in_one.csv") %>%
  dplyr::select(state, lat, lon, NDVI = target, date) %>%
  mutate(lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date)) %>%
  group_by(lat, lon, date, state) %>%
  summarise(NDVI = mean(NDVI))
df2 = read.csv("../data/vi_gee/Landsat/NIRv_in_one.csv") %>%
  dplyr::select(state, lat, lon, NIRv = target, date) %>%
  mutate(lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date)) %>%
  group_by(lat, lon, date, state) %>%
  summarise(NIRv = mean(NIRv))

landsat = full_join(df1, df2, by = c('lat', 'lon', 'state', 'date'))
landsat$state[which(landsat$state == "")] = "Not_Defined"
rm(df1, df2); gc()

landsat %>% group_by(state) %>% 
  summarise(mean_ndvi = mean(NDVI), sd_ndvi = sd(NDVI), 
            mean_NIRv = mean(NIRv), sd_NIRv = sd(NIRv))

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

